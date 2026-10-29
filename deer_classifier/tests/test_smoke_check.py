import unittest

from smoke_check import parse_frame, summarize


def session(states=(0, 1, 0)):
    rows = [{"type": "serial", "line": "READY model_bytes=499712 threshold=0.8500 window=3 required=2"}]
    n = 0
    history = []
    for name, present in zip(("baseline", "deer", "clear"), states):
        rows.append({"type": "stage", "stage": name})
        for _ in range(6):
            n += 1
            score = 0.9 if present else 0.1
            history.append(bool(present))
            history = history[-3:]
            gate = int(sum(history) >= 2)
            rows.append({"type": "serial", "line": f"FRAME n={n} score={score} present={gate} infer_ms=100"})
    return rows


class SmokeTests(unittest.TestCase):
    def test_complete_physical_protocol(self):
        self.assertTrue(summarize(session(), frames=3)["pass"])

    def test_always_deer_and_never_deer_fail(self):
        for states in ((1, 1, 1), (0, 0, 0)):
            self.assertFalse(summarize(session(states), frames=3)["pass"])

    def test_errors_even_during_settle_fail(self):
        rows = session()
        rows.insert(3, {"type": "serial", "line": "ERROR n=1 reason=jpeg_decode present=0"})
        self.assertFalse(summarize(rows, frames=3)["pass"])

    def test_reboot_or_incomplete_capture_fails(self):
        rows = session()
        self.assertFalse(summarize(rows[:-2], frames=3)["pass"])
        rows.insert(7, {"type": "serial", "line": "READY"})
        self.assertFalse(summarize(rows, frames=3)["pass"])

    def test_invalid_scores_are_rejected(self):
        for score in ("nan", "inf", "-0.1", "1.1"):
            with self.assertRaises(ValueError):
                parse_frame(f"FRAME n=1 score={score} present=0")

    def test_counter_restart_fails(self):
        rows = session()
        rows[-1]["line"] = "FRAME n=1 score=0.0 present=0"
        self.assertFalse(summarize(rows, frames=3)["pass"])

    def test_panic_before_reboot_ready_is_not_ignored(self):
        rows = session()
        rows.insert(6, {"type": "serial", "line": "Guru Meditation Error: Core 0 panic'ed"})
        self.assertFalse(summarize(rows, frames=3)["pass"])

    def test_impossible_gate_output_cannot_pass(self):
        rows = session()
        rows[5]["line"] = "FRAME n=4 score=0.9 present=1"
        self.assertFalse(summarize(rows, frames=3)["pass"])

    def test_replay_cannot_weaken_phase_requirements(self):
        self.assertFalse(summarize(session(), frames=2, settle=0)["pass"])

    def test_failed_startup_checks_do_not_pass(self):
        rows = session()
        rows.insert(0, {"type": "serial", "line": "INFERENCE_SELFTEST FAIL score=nan"})
        self.assertFalse(summarize(rows, frames=3)["pass"])


if __name__ == "__main__":
    unittest.main()
