"""Record a physical blank / printed deer / blank serial smoke test.

Run after flashing firmware/smoke_test, with other serial monitors closed.
This checks one controlled demonstration, not field accuracy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
import queue
import threading
import time

STAGES = ("baseline", "deer", "clear")
FRAME = re.compile(r"^FRAME n=(\d+) score=(\S+) present=([01])(?:\s|$)")


def parse_frame(line: str) -> dict | None:
    if not line.startswith("FRAME"):
        return None
    match = FRAME.match(line)
    if not match:
        raise ValueError(f"malformed firmware frame: {line}")
    score = float(match[2])
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError(f"invalid detection score: {score}")
    return {"n": int(match[1]), "score": score, "present": int(match[3])}


def summarize(records: list[dict], frames: int = 10, settle: int = 3) -> dict:
    """Require complete stages, no device errors/reboots and expected gate states."""
    reasons: list[str] = []
    if type(frames) is not int or type(settle) is not int or frames < 3 or settle < 3:
        return {"pass": False, "stages": {}, "failures": ["require at least 3 measured and 3 settling frames"],
                "scope": "controlled printed-image smoke test only"}
    stage_frames: dict[str, list[dict]] = {s: [] for s in STAGES}
    stages_seen: list[str] = []
    previous_n = 0
    active = None
    ready = False
    history: list[bool | None] = []
    threshold = 0.85
    for row in records:
        if row.get("type") == "stage":
            active = row["stage"]
            stages_seen.append(active)
        if row.get("type") != "serial":
            continue
        line = row["line"]
        if line.startswith(("ERROR", "FATAL", "MODEL_SELFTEST FAIL", "GATE_SELFTEST FAIL", "INFERENCE_SELFTEST FAIL")):
            reasons.append(line)
        if ready and (line.startswith(("BOOT ", "ESP-ROM:", "rst:")) or "Guru Meditation" in line or "panic" in line.lower()):
            reasons.append("device reset or panicked during the test: " + line)
        if line.startswith("READY"):
            if ready:
                reasons.append("device restarted during the test")
            ready = True
            threshold_match = re.search(r"\bthreshold=(\S+)", line)
            if threshold_match:
                try:
                    threshold = float(threshold_match[1])
                except ValueError:
                    reasons.append("invalid threshold in READY line")
            if not math.isfinite(threshold) or not 0.10 <= threshold <= 1:
                reasons.append("gate threshold is below the reported score floor or invalid")
            history.clear()
        try:
            frame = parse_frame(line)
        except ValueError as error:
            reasons.append(str(error))
            continue
        if frame is not None:
            if not ready:
                continue
            if previous_n and frame["n"] != previous_n + 1:
                reasons.append("frame counter restarted, repeated or skipped")
            previous_n = frame["n"]
            # Scores have four decimals. Only check gate consistency when rounding
            # cannot change which side of the threshold the actual score was on.
            history.append(None if abs(frame["score"] - threshold) < 0.000051 else frame["score"] >= threshold)
            history = history[-3:]
            if None not in history and frame["present"] != int(sum(history) >= 2):
                reasons.append(f"frame {frame['n']}: gate state disagrees with reported scores")
            if active in stage_frames:
                stage_frames[active].append(frame)
    if stages_seen != list(STAGES):
        reasons.append("expected exactly baseline, deer, clear in that order")
    results = {}
    for stage in STAGES:
        rows = stage_frames[stage]
        measured = rows[settle:settle + frames]
        complete = len(rows) >= settle + frames
        positives = sum(row["present"] for row in measured)
        passed = complete and (positives >= 2 if stage == "deer" else positives == 0)
        if not passed:
            reasons.append(f"{stage}: incomplete capture or unexpected deer signal")
        results[stage] = {"pass": passed, "frames": len(measured),
                          "confirmed_frames": positives,
                          "max_score": max((r["score"] for r in measured), default=None)}
    if not any(r.get("type") == "serial" and r["line"].startswith("READY") for r in records):
        reasons.append("firmware READY line missing")
    return {"pass": not reasons, "stages": results, "failures": reasons,
            "scope": "controlled printed-image smoke test only"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--port", help="Serial device, e.g. COM5 or /dev/ttyACM0")
    source.add_argument("--replay", type=Path, help="Recheck a previously recorded JSONL test")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--frames", type=int, default=10, help="Measured frames per phase (at least 3)")
    parser.add_argument("--settle", type=int, default=3, help="Discard frames after each scene change (at least 3)")
    parser.add_argument("--timeout", type=float, default=120, help="Seconds allowed for startup and each phase")
    parser.add_argument("--log", type=Path, help="Output JSONL; defaults to artifacts/smoke/<UTC time>.jsonl")
    args = parser.parse_args()
    if args.frames < 3 or args.settle < 3 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("require --frames >= 3, --settle >= 3 and a positive finite --timeout")
    if args.replay:
        records = [json.loads(line) for line in args.replay.read_text().splitlines() if line.strip()]
        settings = next((r for r in records if r.get("type") == "settings"), {})
        result = summarize(records, settings.get("frames", args.frames), settings.get("settle", args.settle))
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    try:
        import serial
    except ImportError:
        parser.error("install pyserial first: python -m pip install -r requirements-smoke.txt")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = args.log or Path(__file__).parent / "artifacts" / "smoke" / f"{stamp}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    # Exclusive create keeps earlier physical evidence intact.
    with log_path.open("x", encoding="utf-8") as log:
        lock = threading.Lock()
        def record(row: dict) -> None:
            row["utc"] = datetime.now(timezone.utc).isoformat()
            with lock:
                records.append(row)
                log.write(json.dumps(row) + "\n")
                log.flush()

        record({"type": "settings", "port": args.port, "baud": args.baud,
                "frames": args.frames, "settle": args.settle})
        try:
            with serial.Serial(args.port, args.baud, timeout=1) as device:
                # Avoid requesting an automatic reset via control lines.
                device.dtr = False
                device.rts = False
                incoming: queue.Queue = queue.Queue()
                stopping = threading.Event()
                def reader() -> None:
                    try:
                        while not stopping.is_set():
                            line = device.readline().decode("utf-8", errors="replace").strip()
                            if line:
                                record({"type": "serial", "line": line})
                                incoming.put((time.monotonic(), line))
                    except OSError as error:
                        line = f"ERROR reader={error}"
                        record({"type": "serial", "line": line})
                        incoming.put((time.monotonic(), line))
                worker = threading.Thread(target=reader, daemon=True)
                worker.start()
                print("Press RESET on the Feather. Waiting for firmware READY...")
                def read_line(after: float = 0) -> str:
                    try:
                        received, line = incoming.get(timeout=1)
                    except queue.Empty:
                        return ""
                    if received >= after:
                        print(line, flush=True)
                        if line.startswith(("ERROR", "FATAL", "MODEL_SELFTEST FAIL")):
                            raise RuntimeError(line)
                        return line
                    return ""

                deadline = time.monotonic() + args.timeout
                while time.monotonic() < deadline:
                    if read_line().startswith("READY"):
                        break
                else:
                    raise TimeoutError("firmware did not become READY; check serial console, PSRAM and wiring")
                prompts = (
                    "Aim at an empty background with no deer picture.",
                    "Show a well-lit printed deer image, filling roughly half the camera view.",
                    "Remove the deer picture and show the empty background again.",
                )
                for stage, prompt in zip(STAGES, prompts):
                    input(f"\n{prompt} Press Enter when ready: ")
                    record({"type": "stage", "stage": stage})
                    phase_started = time.monotonic()
                    count = 0
                    deadline = time.monotonic() + args.timeout
                    while count < args.frames + args.settle and time.monotonic() < deadline:
                        count += parse_frame(read_line(phase_started)) is not None
                    if count < args.frames + args.settle:
                        raise TimeoutError(f"not enough frames during {stage}")
                stopping.set()
                worker.join(timeout=2)
                if worker.is_alive():
                    device.cancel_read()
                    worker.join(timeout=2)
                    record({"type": "serial", "line": "ERROR serial_reader_did_not_stop_promptly"})
        except (OSError, RuntimeError, ValueError, TimeoutError, KeyboardInterrupt, EOFError) as error:
            if 'stopping' in locals():
                stopping.set()
                worker.join(timeout=2)
            record({"type": "serial", "line": f"ERROR host={error}"})
        result = summarize(records, args.frames, args.settle)
        record({"type": "summary", **result})
    print(json.dumps(result, indent=2))
    print(f"Evidence: {log_path.resolve()}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
