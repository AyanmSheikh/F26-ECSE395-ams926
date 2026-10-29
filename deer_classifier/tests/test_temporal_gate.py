import math
import unittest

from temporal_gate import TemporalDeerGate


class GateTests(unittest.TestCase):
    def test_confirm_and_clear(self):
        gate = TemporalDeerGate()
        self.assertEqual([gate.update(s) for s in (0.9, 0.9, 0.1, 0.1)],
                         [False, True, True, False])

    def test_camera_failure_and_invalid_scores_clear_history(self):
        for invalid in (None, math.nan, math.inf, -0.1, 1.1):
            gate = TemporalDeerGate()
            self.assertFalse(gate.update(0.9))
            if invalid is None:
                self.assertFalse(gate.update(invalid))
            else:
                with self.assertRaises(ValueError):
                    gate.update(invalid)
            self.assertFalse(gate.update(0.9))


if __name__ == "__main__":
    unittest.main()
