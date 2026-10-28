"""Export a trained ESPDet-Pico checkpoint as an int8 ESP32-S3 .espdl model."""

from __future__ import annotations

import argparse
from pathlib import Path

from espdet_compat import load_esp_detection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esp-detection", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True,
                        help="ESPDet-Pico best.pt checkpoint fine-tuned for deer")
    parser.add_argument("--calib-data", type=Path, required=True,
                        help="Images used for int8 calibration")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, nargs=2, default=(224, 224), metavar=("HEIGHT", "WIDTH"))
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    calib_data = args.calib_data.resolve()
    if not checkpoint.is_file():
        parser.error(f"checkpoint not found: {checkpoint}")
    if not calib_data.is_dir():
        parser.error(f"calibration image folder not found: {calib_data}")

    _, Export, quant_espdet = load_esp_detection(args.esp_detection.resolve())
    size = list(args.size)
    Export(str(checkpoint), size)
    onnx_path = checkpoint.with_suffix(".onnx")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    quant_espdet(
        onnx_path=str(onnx_path),
        target="esp32s3",
        num_of_bits=8,
        device="cpu",
        batchsz=32,
        imgsz=size,
        calib_dir=str(calib_data),
        espdl_model_path=str(args.output.resolve()),
    )
    print(f"Quantized ESP32-S3 model written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
