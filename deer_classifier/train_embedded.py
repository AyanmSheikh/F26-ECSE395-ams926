"""Train ESPDet-Pico and export an int8 ESP-DL model for ESP32-S3."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from training_utils import new_run_name, validate_run_name, validate_settings


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
    parser.add_argument("--warmup-epochs", type=float, default=3.0,
                        help="Warmup duration in epochs")
    parser.add_argument("--warmup-bias-lr", type=float, default=0.0,
                        help="Starting bias LR; zero avoids the SGD default's 0.1 spike with AdamW")
    parser.add_argument("--mosaic", type=float, default=0.2, help="Mosaic augmentation probability")
    parser.add_argument("--scale", type=float, default=0.25, help="Random image scale gain")
    parser.add_argument("--cache", choices=("none", "ram", "disk"), default="none")
    parser.add_argument("--close-mosaic", type=int, default=10, help="Disable mosaic for the final N epochs")
    parser.add_argument("--cos-lr", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--amp", action=argparse.BooleanOptionalAction, default=False,
                        help="Enable only after mixed-precision behavior is verified on the training backend")
    parser.add_argument("--train-only", action="store_true",
                        help="Save the selected checkpoint and provenance without exporting or publishing a model")
    parser.add_argument("--device", default="auto", help="auto selects CUDA, MPS, then CPU on the training host")
    parser.add_argument("--run-name", default=None, help="Unique run directory name (default: UTC timestamp)")
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--workers", type=int, default=0, help="Data-loader workers; 0 is portable on Windows")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--overwrite-output", action="store_true",
                        help="Replace an existing deployed model only after a successful export")
    args = parser.parse_args()

    repo = args.esp_detection.resolve()
    runner = Path(__file__).with_name("run_espdet_training.py")
    dataset = args.dataset.resolve()
    calib_data = (args.calib_data or (dataset / "images/train")).resolve()
    if not args.python.is_file():
        parser.error(f"Python interpreter not found: {args.python}")
    if not (repo / "train.py").is_file() or not (repo / "deploy/quantize.py").is_file():
        parser.error(f"ESP-Detection checkout is incomplete: {repo}")
    run_name = args.run_name or new_run_name()
    try:
        validate_run_name(run_name)
        validate_settings(args.size, args.epochs, args.batch_size, args.patience,
                          args.workers, args.learning_rate, args.warmup_epochs,
                          warmup_bias_lr=args.warmup_bias_lr, mosaic=args.mosaic, scale=args.scale,
                          cache=args.cache, close_mosaic=args.close_mosaic)
    except ValueError as error:
        parser.error(str(error))
    if args.output.exists() and not args.overwrite_output and not args.train_only:
        parser.error(f"model already exists: {args.output}; choose --output artifacts/candidate.espdl or explicitly --overwrite-output")
    if (args.output.parent / run_name).exists():
        parser.error(f"run directory already exists: {args.output.parent / run_name}; choose a new --run-name")
    for folder in (dataset / "images/train", dataset / "images/val",
                   dataset / "labels/train", dataset / "labels/val"):
        if not folder.is_dir():
            parser.error(f"YOLO dataset folder not found: {folder}")
    if not args.pretrained.is_file():
        parser.error(f"checkpoint not found: {args.pretrained}")
    if not args.train_only and not calib_data.is_dir():
        parser.error(f"calibration image folder not found: {calib_data}")

    config = args.output.parent / f"{run_name}_dataset.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    with config.open("x", encoding="utf-8") as stream:
        stream.write(
            f"path: {json.dumps(dataset.as_posix())}\n"
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
        "--run-name", run_name,
        "--patience", str(args.patience),
        "--workers", str(args.workers),
        "--seed", str(args.seed),
        "--warmup-bias-lr", str(args.warmup_bias_lr),
        "--mosaic", str(args.mosaic),
        "--scale", str(args.scale),
        "--cache", args.cache,
        "--close-mosaic", str(args.close_mosaic),
        "--cos-lr" if args.cos_lr else "--no-cos-lr",
        "--amp" if args.amp else "--no-amp",
    ]
    if args.train_only:
        command.append("--train-only")
    if args.overwrite_output:
        command.append("--overwrite-output")
    command += ["--learning-rate", str(args.learning_rate)]
    command += ["--warmup-epochs", str(args.warmup_epochs)]
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=repo, check=True)


if __name__ == "__main__":
    main()
