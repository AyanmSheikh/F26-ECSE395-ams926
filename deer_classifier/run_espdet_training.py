"""Internal runner: invoke Espressif training/export/quantization with safe defaults."""

from __future__ import annotations

import argparse
from pathlib import Path

from espdet_compat import load_esp_detection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esp-detection", type=Path, required=True)
    parser.add_argument("--pretrained_path", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--size", type=int, nargs=2, required=True)
    parser.add_argument("--calib_data", type=Path, required=True)
    parser.add_argument("--espdl", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--optimizer", default="AdamW")
    parser.add_argument("--learning-rate", type=float, default=0.0005)
    parser.add_argument("--warmup-epochs", type=float, default=0.5)
    parser.add_argument("--device", default="mps")
    args = parser.parse_args()

    repo = args.esp_detection.resolve()
    Train, Export, quant_espdet = load_esp_detection(repo)

    size = list(args.size)
    train_settings = dict(
        pretrained_path=str(args.pretrained_path.resolve()),
        dataset=str(args.dataset.resolve()),
        imgsz=size[0] if size[0] == size[1] else size,
        epochs=args.epochs,
        batch=args.batch,
        device=args.device,
        workers=4,
        patience=8,
        close_mosaic=5,
        cache=False,
        project=str(args.espdl.resolve().parent),
        name="deer_espdet_pico",
        exist_ok=True,
        plots=False,
        optimizer=args.optimizer,
    )
    train_settings["lr0"] = args.learning_rate
    train_settings["warmup_epochs"] = args.warmup_epochs
    results = Train(**train_settings)
    best_model = Path(results.save_dir) / "weights/best.pt"
    if not best_model.is_file():
        raise FileNotFoundError(f"training did not produce {best_model}")

    Export(str(best_model), size)
    onnx_path = best_model.with_suffix(".onnx")
    quant_espdet(
        onnx_path=str(onnx_path),
        target="esp32s3",
        num_of_bits=8,
        device="cpu",
        batchsz=32,
        imgsz=size,
        calib_dir=str(args.calib_data.resolve()),
        espdl_model_path=str(args.espdl.resolve()),
    )
    print(f"Quantized ESP32-S3 model written to {args.espdl.resolve()}")


if __name__ == "__main__":
    main()
