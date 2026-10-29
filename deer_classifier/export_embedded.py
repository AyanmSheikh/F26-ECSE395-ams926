"""Export a trained ESPDet-Pico checkpoint as an int8 ESP32-S3 .espdl model."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from espdet_compat import load_esp_detection
from training_utils import (deploy_model, new_run_name, provenance, validate_run_name,
                            validate_settings, write_json)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esp-detection", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True,
                        help="ESPDet-Pico best.pt checkpoint fine-tuned for deer")
    parser.add_argument("--calib-data", type=Path, required=True,
                        help="Images used for int8 calibration")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, nargs=2, default=(224, 224), metavar=("HEIGHT", "WIDTH"))
    parser.add_argument("--run-name", default=None, help="Unique directory for export sidecars and provenance")
    parser.add_argument("--overwrite-output", action="store_true",
                        help="Replace an existing model only when the new export succeeds")
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    calib_data = args.calib_data.resolve()
    output = args.output.resolve()
    run_name = args.run_name or f"{new_run_name()}_export"
    try:
        validate_run_name(run_name)
        validate_settings(args.size, 1, 1, 0, 0, 0.0005, 0)
    except ValueError as error:
        parser.error(str(error))
    run_dir = output.parent / run_name
    if run_dir.exists():
        parser.error(f"export directory already exists: {run_dir}")
    if output.exists() and not args.overwrite_output:
        parser.error(f"model already exists: {output}; choose a candidate path or --overwrite-output")
    if not checkpoint.is_file():
        parser.error(f"checkpoint not found: {checkpoint}")
    if not calib_data.is_dir():
        parser.error(f"calibration image folder not found: {calib_data}")

    _, Export, quant_espdet = load_esp_detection(args.esp_detection.resolve())
    size = list(args.size)
    run_dir.mkdir(parents=True)
    local_checkpoint = run_dir / checkpoint.name
    shutil.copyfile(checkpoint, local_checkpoint)
    manifest = provenance(args.esp_detection.resolve(), checkpoint,
                          {"size": size, "target": "esp32s3", "bits": 8,
                           "calibration_directory": str(calib_data)})
    manifest_path = run_dir / "deer_export.json"
    manifest["status"] = "export pending"
    write_json(manifest_path, manifest)
    Export(str(local_checkpoint), size)
    onnx_path = local_checkpoint.with_suffix(".onnx")
    candidate = run_dir / output.name
    quant_espdet(
        onnx_path=str(onnx_path),
        target="esp32s3",
        num_of_bits=8,
        device="cpu",
        batchsz=32,
        imgsz=size,
        calib_dir=str(calib_data),
        espdl_model_path=str(candidate),
    )
    manifest["artifact"] = deploy_model(candidate, output, overwrite=args.overwrite_output)
    manifest["status"] = "exported; hardware validation pending"
    write_json(manifest_path, manifest)
    print(f"Quantized ESP32-S3 model written to {output}; provenance: {manifest_path}")


if __name__ == "__main__":
    main()
