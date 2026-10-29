"""Internal runner: invoke Espressif training/export/quantization with safe defaults."""

from __future__ import annotations

import argparse
from pathlib import Path

from espdet_compat import load_esp_detection
from training_utils import (deploy_model, new_run_name, provenance, select_device,
                            sha256, validate_run_name, validate_settings, write_json)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esp-detection", type=Path, required=True)
    parser.add_argument("--pretrained_path", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--size", type=int, nargs=2, required=True)
    parser.add_argument("--calib_data", type=Path)
    parser.add_argument("--espdl", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--optimizer", default="AdamW")
    parser.add_argument("--learning-rate", type=float, default=0.0005)
    parser.add_argument("--warmup-epochs", type=float, default=3.0)
    parser.add_argument("--warmup-bias-lr", type=float, default=0.0)
    parser.add_argument("--mosaic", type=float, default=0.2)
    parser.add_argument("--scale", type=float, default=0.25)
    parser.add_argument("--cache", choices=("none", "ram", "disk"), default="none")
    parser.add_argument("--close-mosaic", type=int, default=10)
    parser.add_argument("--cos-lr", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--amp", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--train-only", action="store_true")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--overwrite-output", action="store_true")
    args = parser.parse_args()

    repo = args.esp_detection.resolve()
    output = args.espdl.resolve()
    run_name = args.run_name or new_run_name()
    try:
        validate_run_name(run_name)
        validate_settings(args.size, args.epochs, args.batch, args.patience,
                          args.workers, args.learning_rate, args.warmup_epochs,
                          warmup_bias_lr=args.warmup_bias_lr, mosaic=args.mosaic, scale=args.scale,
                          cache=args.cache, close_mosaic=args.close_mosaic)
    except ValueError as error:
        parser.error(str(error))
    run_dir = output.parent / run_name
    if run_dir.exists():
        parser.error(f"run directory already exists: {run_dir}")
    if output.exists() and not args.overwrite_output and not args.train_only:
        parser.error(f"model already exists: {output}; choose a candidate path or --overwrite-output")
    if not args.train_only and (args.calib_data is None or not args.calib_data.is_dir()):
        parser.error("export requires --calib_data pointing to a calibration image directory")
    Train, Export, quant_espdet = load_esp_detection(repo)
    device = select_device(args.device)
    print(f"Training device: {device}; preserving run in {run_dir}")

    size = list(args.size)
    train_settings = dict(
        pretrained_path=str(args.pretrained_path.resolve()),
        dataset=str(args.dataset.resolve()),
        imgsz=size[0] if size[0] == size[1] else size,
        epochs=args.epochs,
        batch=args.batch,
        device=device,
        workers=args.workers,
        patience=args.patience,
        seed=args.seed,
        close_mosaic=args.close_mosaic,
        cache=False if args.cache == "none" else args.cache,
        mosaic=args.mosaic,
        scale=args.scale,
        cos_lr=args.cos_lr,
        amp=args.amp,
        project=str(output.parent),
        name=run_name,
        exist_ok=False,
        plots=False,
        # Preserve intermediate candidates for image-presence comparisons;
        # detector mAP and the firmware's deer/no-deer objective can differ.
        save_period=5,
        optimizer=args.optimizer,
    )
    train_settings["lr0"] = args.learning_rate
    train_settings["warmup_epochs"] = args.warmup_epochs
    train_settings["warmup_bias_lr"] = args.warmup_bias_lr
    manifest = provenance(repo, args.pretrained_path.resolve(), train_settings)
    manifest["dataset_yaml_sha256"] = sha256(args.dataset.resolve())
    results = Train(**train_settings)
    run_dir = Path(results.save_dir)
    manifest_path = run_dir / "deer_run.json"
    manifest["status"] = "trained; export pending"
    write_json(manifest_path, manifest)
    best_model = run_dir / "weights/best.pt"
    if not best_model.is_file():
        raise FileNotFoundError(f"training did not produce {best_model}")
    manifest["selected_checkpoint"] = str(best_model.resolve())
    manifest["selected_checkpoint_sha256"] = sha256(best_model)
    write_json(manifest_path, manifest)
    if args.train_only:
        print(f"Training complete; selected checkpoint: {best_model.resolve()}; "
              f"export pending; provenance: {manifest_path}")
        return

    Export(str(best_model), size)
    onnx_path = best_model.with_suffix(".onnx")
    export_dir = run_dir / "export"
    export_dir.mkdir()
    candidate = export_dir / output.name
    quant_espdet(
        onnx_path=str(onnx_path),
        target="esp32s3",
        num_of_bits=8,
        device="cpu",
        batchsz=32,
        imgsz=size,
        calib_dir=str(args.calib_data.resolve()),
        espdl_model_path=str(candidate),
    )
    manifest["quantization"] = {"target": "esp32s3", "bits": 8, "calibration_directory": str(args.calib_data.resolve()), "size": size}
    manifest["artifact"] = deploy_model(candidate, output, overwrite=args.overwrite_output)
    manifest["status"] = "exported; hardware validation pending"
    write_json(manifest_path, manifest)
    print(f"Quantized ESP32-S3 model written to {output}; provenance: {manifest_path}")


if __name__ == "__main__":
    main()
