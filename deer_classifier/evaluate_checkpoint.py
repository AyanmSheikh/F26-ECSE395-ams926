"""Validate an ESPDet-Pico checkpoint on the held-out deer dataset split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from espdet_compat import load_esp_detection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esp-detection", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--device", default="mps")
    parser.add_argument("--size", type=int, nargs=2, default=(224, 224), metavar=("HEIGHT", "WIDTH"))
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    data = args.data.resolve()
    if not checkpoint.is_file():
        parser.error(f"checkpoint not found: {checkpoint}")
    if not data.is_file():
        parser.error(f"dataset YAML not found: {data}")

    load_esp_detection(args.esp_detection.resolve())
    from ultralytics import YOLO

    model = YOLO(str(checkpoint))
    results = model.val(
        data=str(data),
        imgsz=list(args.size),
        batch=args.batch_size,
        device=args.device,
        workers=0,
        plots=False,
    )
    print(json.dumps(results.results_dict, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
