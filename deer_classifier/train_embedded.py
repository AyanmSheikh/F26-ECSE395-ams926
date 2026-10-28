"""Train ESPDet-Pico and export an int8 ESP-DL model for ESP32-S3."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esp-detection", type=Path, required=True,
                        help="Path to a checkout of Espressif's esp-detection repository")
    parser.add_argument("--python", type=Path, default=Path(sys.executable),
                        help="Python interpreter in the environment with ESP-Detection dependencies")
    parser.add_argument("--dataset", type=Path, required=True,
                        help="YOLO dataset root containing images/{train,val} and labels/{train,val}")
    parser.add_argument("--pretrained", type=Path, required=True,
                        help="ESPDet-Pico pretrained checkpoint supported by esp-detection")
    parser.add_argument("--calib-data", type=Path,
                        help="Calibration images (defaults to training images)")
    parser.add_argument("--output", type=Path, default=Path("artifacts/deer.espdl"))
    parser.add_argument("--size", type=int, nargs=2, default=(224, 224), metavar=("HEIGHT", "WIDTH"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--optimizer", default="AdamW", help="Ultralytics optimizer, e.g. auto or AdamW")
    parser.add_argument("--learning-rate", type=float, default=0.0005,
                        help="Initial LR (used with a named optimizer; auto chooses its own LR)")
    parser.add_argument("--warmup-epochs", type=float, default=0.5,
                        help="Warmup duration in epochs")
    parser.add_argument("--device", default="mps", help="Ultralytics device, e.g. mps or cpu")
    args = parser.parse_args()

    repo = args.esp_detection.resolve()
    runner = Path(__file__).with_name("run_espdet_training.py")
    dataset = args.dataset.resolve()
    calib_data = (args.calib_data or (dataset / "images/train")).resolve()
    if not args.python.is_file():
        parser.error(f"Python interpreter not found: {args.python}")
    if not (repo / "train.py").is_file() or not (repo / "deploy/quantize.py").is_file():
        parser.error(f"ESP-Detection checkout is incomplete: {repo}")
    if args.epochs < 1 or args.batch_size < 1:
        parser.error("--epochs and --batch-size must be positive")
    for folder in (dataset / "images/train", dataset / "images/val",
                   dataset / "labels/train", dataset / "labels/val"):
        if not folder.is_dir():
            parser.error(f"YOLO dataset folder not found: {folder}")
    if not args.pretrained.is_file():
        parser.error(f"checkpoint not found: {args.pretrained}")
    if not calib_data.is_dir():
        parser.error(f"calibration image folder not found: {calib_data}")

    config = args.output.parent / "deer_dataset.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        f"path: {dataset.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n  0: deer\n"
    )
    command = [
        str(args.python.resolve()), str(runner),
        "--esp-detection", str(repo),
        "--pretrained_path", str(args.pretrained.resolve()),
        "--dataset", str(config.resolve()),
        "--size", str(args.size[0]), str(args.size[1]),
        "--calib_data", str(calib_data),
        "--espdl", str(args.output.resolve()),
        "--epochs", str(args.epochs),
        "--batch", str(args.batch_size),
        "--optimizer", args.optimizer,
        "--device", args.device,
    ]
    command += ["--learning-rate", str(args.learning_rate)]
    command += ["--warmup-epochs", str(args.warmup_epochs)]
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=repo, check=True)


if __name__ == "__main__":
    main()
