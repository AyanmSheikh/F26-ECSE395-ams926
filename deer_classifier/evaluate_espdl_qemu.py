"""Prepare held-out RGB frames and score exact ESP32-S3 QEMU inference logs.

The firmware executes the retained .espdl file. Host Pillow decoding and optional
bilinear downsampling precede ESP-DL preprocessing. QEMU timing is not physical
ESP32 timing, and these still-image metrics do not evaluate the temporal gate.
Accuracy reports require supplied run metadata and a hash-checked passing
numerical-oracle log. The installed QEMU failed that test; its scores must not
be used as model accuracy. Checking supplied evidence does not certify hardware.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import re
import struct

from image_metrics import read_deer_label, sha256_file, summarize_presence

MAGIC = b"DEERDS01"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
HASH = re.compile(r"^[0-9a-f]{64}$")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
RESULT = re.compile(r"^RESULT id=(\d+) score=(\S+)(?:\s|$)")


def write_json_exclusive(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def decode_log(raw: bytes) -> str:
    """Accept UTF-8 and Windows PowerShell's UTF-16 redirected logs."""
    return raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8", errors="replace")


def load_validated_run_metadata(path: Path) -> dict:
    """Check caller-provided numerical evidence before allowing an accuracy report.

    Expected metadata includes numeric_oracle_passed=true, qemu_exit_code=0 and
    oracle_log={path, sha256}. Relative oracle paths resolve beside this metadata.
    The caller must run that oracle on the same emulator/runtime as evaluation;
    this is a provenance check, not independent certification of that assertion.
    """
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or metadata.get("numeric_oracle_passed") is not True:
        raise ValueError("Accuracy report blocked: require numeric_oracle_passed=true; "
                         "the installed QEMU failed CPU golden-tensor validation")
    if type(metadata.get("qemu_exit_code")) is not int or metadata["qemu_exit_code"] != 0:
        raise ValueError("Accuracy report blocked: require qemu_exit_code=0")
    evidence = metadata.get("oracle_log")
    if (not isinstance(evidence, dict) or not isinstance(evidence.get("path"), str)
            or not isinstance(evidence.get("sha256"), str) or not HASH.fullmatch(evidence["sha256"])):
        raise ValueError("Accuracy report blocked: require oracle_log path and SHA-256 evidence")
    oracle_path = Path(evidence["path"])
    if not oracle_path.is_absolute():
        oracle_path = path.resolve().parent / oracle_path
    if sha256_file(oracle_path) != evidence["sha256"]:
        raise ValueError("Accuracy report blocked: numerical-oracle log SHA-256 does not match")
    lines = [ANSI.sub("", line).strip() for line in decode_log(oracle_path.read_bytes()).splitlines()]
    if "MODEL_SELFTEST PASS" not in lines or any(
            line.startswith(("ERROR", "FATAL", "MODEL_SELFTEST FAIL"))
            or re.match(r"^E \(\d+\)", line)
            or any(marker in line.lower() for marker in ("guru meditation", "panic", "assert failed", "abort()"))
            for line in lines):
        raise ValueError("Accuracy report blocked: oracle evidence must contain MODEL_SELFTEST PASS and no errors")
    return metadata


def prepare_frames(dataset: Path, output_dir: Path, model: Path, *, max_side: int = 320,
                   limit: int | None = None, seed: int = 395) -> dict:
    """Snapshot explicit val image/label pairs into the firmware input protocol."""
    if not 1 <= max_side <= 320:
        raise ValueError("max_side must be in [1, 320]")
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    dataset, model = dataset.resolve(), model.resolve()
    image_dir, label_dir = dataset / "images/val", dataset / "labels/val"
    if not image_dir.is_dir() or not label_dir.is_dir():
        raise ValueError("dataset must contain images/val and labels/val")
    if not model.is_file():
        raise FileNotFoundError(f"Model not found: {model}")
    paths = sorted((p for p in image_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES),
                   key=lambda p: p.relative_to(image_dir).as_posix())
    available_count = len(paths)
    if not paths:
        raise ValueError("No held-out images found")
    if limit is not None and limit < len(paths):
        paths = sorted(random.Random(seed).sample(paths, limit))
    # Validate all labels before creating the binary. Missing labels are not negatives.
    labels = [label_dir / image.relative_to(image_dir).with_suffix(".txt") for image in paths]
    truth = [read_deer_label(label) for label in labels]
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    binary, manifest_path = output_dir / "frames.bin", output_dir / "frames.json"
    if binary.exists() or manifest_path.exists():
        raise FileExistsError("frames.bin or frames.json already exists; choose a new --out-dir")

    from PIL import Image
    import PIL

    rows = []
    created_binary = False
    try:
        with binary.open("xb") as output:
            created_binary = True
            output.write(MAGIC)
            output.write(struct.pack("<I", len(paths)))
            for sample_id, (image, label, has_deer) in enumerate(zip(paths, labels, truth, strict=True)):
                with Image.open(image) as source:
                    pixels = source.convert("RGB")
                original_size = pixels.size
                scale = min(1.0, max_side / max(pixels.size))
                if scale < 1:
                    size = tuple(max(1, round(dimension * scale)) for dimension in pixels.size)
                    pixels = pixels.resize(size, resample=Image.Resampling.BILINEAR)
                rgb = pixels.tobytes()
                width, height = pixels.size
                output.write(struct.pack("<III", sample_id, width, height))
                output.write(rgb)
                rows.append({
                    "id": sample_id, "image": str(image),
                    "relative_image": image.relative_to(image_dir).as_posix(),
                    "image_sha256": sha256_file(image), "label": str(label),
                    "label_sha256": sha256_file(label), "has_deer": has_deer,
                    "original_width": original_size[0], "original_height": original_size[1],
                    "width": width, "height": height,
                    "rgb_sha256": hashlib.sha256(rgb).hexdigest(),
                })
        manifest = {
            "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
            "protocol": MAGIC.decode("ascii"), "dataset": str(dataset), "split": "val",
            "classes": {"0": "deer"}, "available_validation_images": available_count,
            "image_count": len(rows), "deer_images": sum(truth),
            "selection": "all available validation images" if len(rows) == available_count else "deterministic random subset",
            "selection_seed": seed if len(rows) != available_count else None,
            "model": {"path": str(model), "size_bytes": model.stat().st_size, "sha256": sha256_file(model)},
            "frames_file": {"path": str(binary), "size_bytes": binary.stat().st_size, "sha256": sha256_file(binary)},
            "preprocessing": {"host": "Pillow RGB decode, no EXIF rotation, optional bilinear resize without crop",
                              "pillow_version": PIL.__version__, "maximum_side": max_side,
                              "firmware": "ESP-DL centered letterbox 224x224 RGB114, channels/255, int8 quantization"},
            "images": rows,
        }
        recovery = dataset / "recovery_manifest.json"
        if recovery.is_file():
            manifest["dataset_recovery"] = {"path": str(recovery), "sha256": sha256_file(recovery)}
        write_json_exclusive(manifest_path, manifest)
    except BaseException:
        # Only this function's exclusive-created partial binary is removed.
        if created_binary:
            binary.unlink(missing_ok=True)
        raise
    return manifest


def parse_results(log_text: str, manifest: dict, thresholds=(0.10, 0.25, 0.50, 0.70, 0.85, 0.95)) -> dict:
    """Parse protocol and metric arithmetic; this alone does not validate QEMU math."""
    if manifest.get("protocol") != MAGIC.decode("ascii"):
        raise ValueError("Unrecognized frames manifest protocol")
    if not thresholds or any(not math.isfinite(t) or not 0.10 <= t <= 1 for t in thresholds):
        raise ValueError("thresholds must be in [0.10, 1], at or above the firmware score floor")
    expected = {}
    for row in manifest["images"]:
        sample_id = row["id"]
        if type(sample_id) is not int or sample_id < 0 or sample_id in expected:
            raise ValueError("Manifest contains invalid or duplicate sample IDs")
        if type(row["has_deer"]) is not bool or not HASH.fullmatch(row["rgb_sha256"]):
            raise ValueError("Manifest has invalid ground truth or RGB hash")
        expected[sample_id] = row
    if not expected or len(expected) != manifest["image_count"]:
        raise ValueError("Manifest image count is empty or inconsistent")
    model = manifest["model"]
    if not HASH.fullmatch(model["sha256"]):
        raise ValueError("Invalid manifest model hash")
    boot_seen = end_seen = False
    scores = {}
    for raw_line in log_text.splitlines():
        line = ANSI.sub("", raw_line).strip()
        if not line:
            continue
        if (line.startswith(("ERROR", "FATAL", "MODEL_SELFTEST FAIL")) or re.match(r"^E \(\d+\)", line)
                or any(marker in line.lower() for marker in ("guru meditation", "panic", "assert failed", "abort()"))):
            raise ValueError("Device error invalidates evaluation: " + line)
        if boot_seen and line.startswith(("ESP-ROM:", "rst:")):
            raise ValueError("Device reset during evaluation: " + line)
        if line.startswith("BOOT "):
            if boot_seen or end_seen:
                raise ValueError("Repeated boot invalidates evaluation")
            size_match = re.search(r"\bmodel_bytes=(\d+)(?:\s|$)", line)
            hash_match = re.search(r"\bsha256=([0-9a-f]{64})(?:\s|$)", line)
            if (not line.startswith("BOOT dataset_eval ") or not size_match or not hash_match
                    or int(size_match[1]) != model["size_bytes"] or hash_match[1] != model["sha256"]):
                raise ValueError("Firmware model identity does not match manifest")
            boot_seen = True
        elif line.startswith("RESULT"):
            match = RESULT.match(line)
            rgb_match = re.search(r"\brgb_sha256=([0-9a-f]{64})(?:\s|$)", line)
            if not boot_seen or end_seen or not match or not rgb_match:
                raise ValueError("Malformed or out-of-order RESULT: " + line)
            sample_id, score = int(match[1]), float(match[2])
            if sample_id not in expected or sample_id in scores:
                raise ValueError(f"Unexpected or duplicate result ID: {sample_id}")
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError(f"Invalid confidence for sample {sample_id}")
            if rgb_match[1] != expected[sample_id]["rgb_sha256"]:
                raise ValueError(f"RGB input hash mismatch for sample {sample_id}")
            scores[sample_id] = score
        elif line.startswith("END"):
            match = re.fullmatch(r"END count=(\d+)", line)
            if not boot_seen or end_seen or not match or int(match[1]) != len(expected):
                raise ValueError("Missing, malformed or inconsistent END record")
            if set(scores) != set(expected):
                raise ValueError("END reached without exactly one result for every manifest image")
            end_seen = True
    if not boot_seen or not end_seen or set(scores) != set(expected):
        raise ValueError("Incomplete evaluation: require matching BOOT, all RESULTs and END")
    rows = [{**expected[sample_id], "score": scores[sample_id]} for sample_id in sorted(expected)]
    metrics = summarize_presence(rows, list(thresholds))
    for item in metrics:
        specificity = None if item["false_positive_rate"] is None else 1 - item["false_positive_rate"]
        item["balanced_accuracy"] = ((item["recall"] + specificity) / 2
                                     if specificity is not None and item["recall"] is not None else None)
    return {
        "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "execution": "Official ESP32-S3 QEMU executing the unchanged ESP-DL artifact",
        "limitations": ["Host-decoded still images, no physical camera test",
                        "QEMU timing does not measure physical ESP32 latency or energy",
                        "Numerical validation relies on the caller supplying evidence from the same emulator/runtime",
                        "Unordered images do not evaluate the 2-of-3 temporal gate",
                        "Image presence does not require a correctly localized bounding box"],
        "model": model, "dataset": manifest["dataset"], "split": manifest["split"],
        "selection": manifest["selection"], "preprocessing": manifest["preprocessing"],
        "image_count": len(rows), "deer_images": sum(row["has_deer"] for row in rows),
        "non_deer_images": sum(not row["has_deer"] for row in rows),
        "score_contract": "Maximum class-0 deer box confidence after 0.10 candidate filter; zero when none",
        "image_presence": metrics, "images": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--results", type=Path, metavar="SERIAL_LOG")
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/qemu-evaluation"))
    parser.add_argument("--model", type=Path, default=Path(__file__).parent / "artifacts/deer.espdl")
    parser.add_argument("--max-side", type=int, default=320)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seed", type=int, default=395)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--thresholds", type=float, nargs="+", default=(0.10, 0.25, 0.50, 0.70, 0.85, 0.95))
    parser.add_argument("--output", type=Path, default=Path("artifacts/qemu-evaluation.json"))
    parser.add_argument("--run-metadata", type=Path,
                        help="Required for --results: numeric_oracle_passed=true, qemu_exit_code=0, "
                             "oracle_log={path, sha256}; also record emulator version/command/build")
    args = parser.parse_args()
    try:
        if args.prepare:
            if args.dataset is None:
                parser.error("--prepare requires --dataset")
            manifest = prepare_frames(args.dataset, args.out_dir, args.model,
                                      max_side=args.max_side, limit=args.limit, seed=args.seed)
            print(f"Prepared {manifest['image_count']} val images ({manifest['deer_images']} deer) "
                  f"in {args.out_dir.resolve()}")
        else:
            if args.manifest is None:
                parser.error("--results requires --manifest")
            if args.run_metadata is None:
                parser.error("--results requires --run-metadata with passing numerical-oracle evidence; "
                             "a completed inference log does not establish correct QEMU arithmetic")
            run_metadata = load_validated_run_metadata(args.run_metadata)
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            text = decode_log(args.results.read_bytes())
            report = parse_results(text, manifest, args.thresholds)
            report["manifest"] = {"path": str(args.manifest.resolve()), "sha256": sha256_file(args.manifest)}
            report["serial_log"] = {"path": str(args.results.resolve()), "sha256": sha256_file(args.results)}
            report["run_metadata"] = run_metadata
            report["run_metadata_file"] = {"path": str(args.run_metadata.resolve()),
                                            "sha256": sha256_file(args.run_metadata)}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json_exclusive(args.output, report)
            print(json.dumps({key: value for key, value in report.items() if key != "images"}, indent=2))
            print(f"Per-image results: {args.output.resolve()}")
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
