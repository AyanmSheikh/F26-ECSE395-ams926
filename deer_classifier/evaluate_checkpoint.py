"""Evaluate detector mAP and image-level deer presence on one held-out pass.

This evaluates the float checkpoint, not the int8 .espdl runtime. A host result
does not establish camera, quantization, or printed-image performance.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path

from espdet_compat import load_esp_detection
from image_metrics import read_deer_boxes, sha256_file, summarize_presence


class NmsTimeoutWatcher(logging.Handler):
    """Truncated NMS must fail evaluation rather than masquerade as misses."""

    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record):
        message = record.getMessage()
        if "NMS time limit" in message:
            self.messages.append(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esp-detection", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--size", type=int, nargs=2, default=(224, 224), metavar=("HEIGHT", "WIDTH"))
    parser.add_argument("--batch-size", type=int, default=1,
                        help="Small batches avoid the previous truncated-NMS evaluation")
    parser.add_argument("--thresholds", type=float, nargs="+", default=(0.25, 0.50, 0.70, 0.85, 0.95))
    parser.add_argument("--prediction-floor", type=float, default=0.001)
    parser.add_argument("--nms-seconds-per-image", type=float, default=5.0)
    parser.add_argument("--nms-iou", type=float, default=0.7)
    parser.add_argument("--max-detections", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation.json"))
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    data = args.data.resolve()
    if not checkpoint.is_file():
        parser.error(f"checkpoint not found: {checkpoint}")
    if not data.is_file():
        parser.error(f"dataset YAML not found: {data}")
    if args.batch_size < 1 or min(args.size) < 1 or args.max_detections < 1:
        parser.error("batch size, input dimensions, and max detections must be positive")
    if args.size[0] != args.size[1] or any(dimension % 32 for dimension in args.size):
        parser.error("the pinned validator uses square inputs; --size must be equal multiples of 32")
    if not math.isfinite(args.prediction_floor) or not 0 <= args.prediction_floor < 1:
        parser.error("prediction floor must be in [0, 1)")
    if any(not math.isfinite(t) or not args.prediction_floor < t <= 1 for t in args.thresholds):
        parser.error("every threshold must be above the prediction floor and at most 1")
    if not math.isfinite(args.nms_seconds_per_image) or args.nms_seconds_per_image < 0.5:
        parser.error("NMS seconds per image must be finite and at least 0.5 (compatibility bridge minimum)")
    if not math.isfinite(args.nms_iou) or not 0 < args.nms_iou <= 1:
        parser.error("NMS IoU must be in (0, 1]")
    if not (args.esp_detection / "train.py").is_file():
        parser.error(f"ESP-Detection checkout not found: {args.esp_detection}")

    load_esp_detection(args.esp_detection.resolve())
    import torch
    import numpy as np
    import ultralytics
    from ultralytics import YOLO
    from ultralytics.data.utils import img2label_paths
    from ultralytics.models.yolo.detect import DetectionValidator
    from ultralytics.utils import LOGGER, nms

    rows = []
    expected_images = set()
    label_hashes = {}
    label_truth = {}

    class PresenceValidator(DetectionValidator):
        def get_dataloader(self, dataset_path, batch_size):
            loader = super().get_dataloader(dataset_path, batch_size)
            image_paths = loader.dataset.im_files
            if len(loader.dataset.label_files) != len(image_paths):
                raise RuntimeError("Evaluation invalid: dataset scan excluded corrupt images or annotations")
            for image, label, cached in zip(image_paths, img2label_paths(image_paths), loader.dataset.labels, strict=True):
                image = str(Path(image).resolve())
                if image in expected_images:
                    raise ValueError(f"Duplicate held-out image: {image}")
                expected_images.add(image)
                boxes = read_deer_boxes(Path(label))
                # Ultralytics may retain a label cache across edits of equal file size.
                # Compare the actual cached annotations, including box coordinates.
                actual = sorted(tuple(float(v) for v in box) for box in cached["bboxes"])
                wanted = sorted(set(boxes))  # upstream removes exact duplicate boxes
                if len(actual) != len(wanted) or (wanted and not np.allclose(actual, wanted, rtol=0, atol=1e-6)):
                    raise RuntimeError(f"Cached boxes differ from disk; remove stale .cache files: {image}")
                if any(float(c) != 0 for c in cached["cls"].flatten()):
                    raise ValueError(f"Cached annotations contain a class other than deer: {image}")
                label_truth[image] = bool(boxes)
                label_hashes[image] = sha256_file(Path(label))
            return loader

        def update_metrics(self, preds, batch):
            if len(preds) != len(batch["im_file"]):
                raise RuntimeError("Prediction batch does not cover every image")
            for index, pred in enumerate(preds):
                image = str(Path(batch["im_file"][index]).resolve())
                ground_truth = batch["cls"][batch["batch_idx"] == index].flatten()
                if bool((ground_truth == 0).any()) != label_truth[image]:
                    raise RuntimeError(f"Cached labels differ from disk; remove stale .cache files: {image}")
                # Ultralytics 8.4 emits dicts; older compatible validators emit Nx6 tensors.
                if isinstance(pred, dict):
                    scores = pred["conf"][pred["cls"] == 0]
                else:
                    scores = pred[pred[:, 5] == 0, 4]
                rows.append({"image": image, "has_deer": label_truth[image],
                             "label_sha256": label_hashes[image],
                             "score": float(scores.max().item()) if len(scores) else 0.0})
            super().update_metrics(preds, batch)

    model = YOLO(str(checkpoint))
    names = model.names
    if len(names) != 1 or str(names[0]).lower() != "deer":
        parser.error(f"Expected a trained one-class deer checkpoint, got class names: {names}")

    original_nms = nms.non_max_suppression

    def evaluation_nms(*positional, **keyword):
        keyword["max_time_img"] = args.nms_seconds_per_image
        return original_nms(*positional, **keyword)

    watcher = NmsTimeoutWatcher()
    LOGGER.addHandler(watcher)
    nms.non_max_suppression = evaluation_nms
    try:
        results = model.val(
            validator=PresenceValidator, data=str(data), imgsz=args.size[0],
            batch=args.batch_size, device=args.device, workers=0, plots=False,
            conf=args.prediction_floor, iou=args.nms_iou, max_det=args.max_detections,
            rect=False, augment=False,
        )
    finally:
        nms.non_max_suppression = original_nms
        LOGGER.removeHandler(watcher)
    if watcher.messages:
        raise RuntimeError("Evaluation invalid: NMS truncated predictions. Increase the budget. "
                           + "; ".join(watcher.messages))
    if {row["image"] for row in rows} != expected_images:
        raise RuntimeError("Evaluation invalid: not every held-out image produced a result")

    report = {
        "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_format": "float PyTorch checkpoint (not the quantized ESP-DL artifact)",
        "checkpoint": str(checkpoint), "checkpoint_sha256": sha256_file(checkpoint),
        "dataset_yaml": str(data), "dataset_yaml_sha256": sha256_file(data),
        "versions": {"torch": torch.__version__, "ultralytics": ultralytics.__version__},
        "settings": {"input_size": list(args.size), "device": args.device,
                     "batch_size": args.batch_size, "rect": False,
                     "prediction_floor": args.prediction_floor, "nms_iou": args.nms_iou,
                     "max_detections": args.max_detections,
                     "nms_seconds_per_image": args.nms_seconds_per_image},
        "score_contract": "maximum class-0 deer box confidence; zero when no box",
        "image_count": len(rows), "deer_images": sum(row["has_deer"] for row in rows),
        "detector_metrics": {key: float(value) for key, value in results.results_dict.items()},
        "image_presence": summarize_presence(rows, list(args.thresholds)),
        "temporal_gate": "Not evaluated: unordered still images do not constitute frame sequences",
        "images": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "images"}, indent=2, allow_nan=False))
    print(f"Per-image scores and settings written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
