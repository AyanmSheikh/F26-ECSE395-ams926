"""Host preprocessing and one-class decoding matched to the ESP-DL camera path."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random

import numpy as np
from PIL import Image

from image_metrics import read_deer_boxes, sha256_file

OUTPUT_NAMES = ("box0", "score0", "box1", "score1", "box2", "score2")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass(frozen=True)
class Sample:
    image: Path
    label: Path
    boxes: tuple
    image_hash: str
    label_hash: str

    @property
    def positive(self) -> bool:
        return bool(self.boxes)


def collect_split(dataset: Path, split: str) -> list[Sample]:
    image_root = dataset / "images" / split
    label_root = dataset / "labels" / split
    images = sorted(p for p in image_root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise ValueError(f"No images found in {image_root}")
    samples = []
    for image in images:
        label = label_root / image.relative_to(image_root).with_suffix(".txt")
        boxes = tuple(sorted(set(read_deer_boxes(label))))
        samples.append(Sample(image.resolve(), label.resolve(), boxes, sha256_file(image), sha256_file(label)))
    return samples


def assert_disjoint(train: list[Sample], validation: list[Sample]) -> None:
    train_hashes = {sample.image_hash for sample in train}
    for sample in validation:
        if sample.image_hash in train_hashes:
            raise ValueError(f"Training/validation image-content overlap: {sample.image}")
    if len({sample.image_hash for sample in validation}) != len(validation):
        raise ValueError("Validation contains identical image contents more than once")


def manifest_hash(samples: list[Sample]) -> str:
    content = [(sample.image.name, sample.image_hash, sample.label_hash) for sample in samples]
    return hashlib.sha256(json.dumps(content, separators=(",", ":")).encode()).hexdigest()


def select_calibration(samples: list[Sample], count: int, seed: int) -> list[Sample]:
    if count < 2:
        raise ValueError("Balanced calibration requires at least two images")
    positive = [sample for sample in samples if sample.positive]
    negative = [sample for sample in samples if not sample.positive]
    required_positive, required_negative = (count + 1) // 2, count // 2
    if len(positive) < required_positive or len(negative) < required_negative:
        raise ValueError(f"Need {required_positive} deer and {required_negative} confirmed negatives for calibration")
    generator = random.Random(seed)
    selected = generator.sample(positive, required_positive) + generator.sample(negative, required_negative)
    generator.shuffle(selected)
    return selected


def espdl_letterbox(rgb: np.ndarray, size: int = 224) -> tuple[np.ndarray, dict]:
    """Match ESP-DL float32 geometry and floor(i * inverse_scale) sampling.

    Pillow's nearest-neighbor resize uses center-based coordinates, which differ.
    Return RGB888 pixels before /255 and the inverse mapping for box decoding.
    """
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3 or size < 1:
        raise ValueError("Expected a nonempty uint8 RGB image and positive destination size")
    height, width = rgb.shape[:2]
    if min(height, width) < 1:
        raise ValueError("Empty RGB image")
    scale_x, scale_y = np.float32(size) / np.float32(width), np.float32(size) / np.float32(height)
    content_width = content_height = size
    if scale_x < scale_y:
        content_height = int(np.float32(scale_x * np.float32(height)))
    else:
        content_width = int(np.float32(scale_y * np.float32(width)))
    if min(content_width, content_height) < 1:
        raise ValueError("Image aspect ratio collapses the letterboxed content")
    left, top = (size - content_width) // 2, (size - content_height) // 2
    inverse_x, inverse_y = np.float32(width) / np.float32(content_width), np.float32(height) / np.float32(content_height)
    x = np.minimum((np.arange(content_width, dtype=np.float32) * inverse_x).astype(np.int64), width - 1)
    y = np.minimum((np.arange(content_height, dtype=np.float32) * inverse_y).astype(np.int64), height - 1)
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    canvas[top:top + content_height, left:left + content_width] = rgb[y[:, None], x[None, :]]
    return canvas, {"width": width, "height": height, "left": left, "top": top,
                    "inverse_x": float(inverse_x), "inverse_y": float(inverse_y)}


def resolve_capture_max_side(requested: int | None, stored_settings: dict | None = None) -> int:
    """New exports default to a QVGA proxy; native graphs retain calibration preprocessing."""
    stored = stored_settings.get("capture_max_side", 0) if stored_settings is not None else 320
    if type(stored) is not int or stored < 0 or (requested is not None and (type(requested) is not int or requested < 0)):
        raise ValueError("capture-max-side must be a nonnegative integer; 0 selects legacy raw input")
    if stored_settings is not None and requested is not None and requested != stored:
        raise ValueError("Native graph preprocessing must match its saved calibration capture-max-side; create a new export to change it")
    return stored if requested is None else requested


def capture_proxy(rgb: np.ndarray, max_side: int = 320) -> np.ndarray:
    """Aspect-preserving bilinear acquisition proxy, not the actual OV5640 ISP/JPEG path."""
    if type(max_side) is not int or max_side < 0:
        raise ValueError("capture-max-side must be a nonnegative integer")
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) < 1:
        raise ValueError("Expected a nonempty uint8 RGB image")
    height, width = rgb.shape[:2]
    if not max_side or max(width, height) <= max_side:
        return rgb
    scale = max_side / max(width, height)
    dimensions = (max(1, round(width * scale)), max(1, round(height * scale)))
    return np.asarray(Image.fromarray(rgb).resize(dimensions, Image.Resampling.BILINEAR), dtype=np.uint8)


def prepare_image(path: Path, capture_max_side: int = 320) -> tuple[np.ndarray, dict]:
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    source_height, source_width = rgb.shape[:2]
    canvas, mapping = espdl_letterbox(capture_proxy(rgb, capture_max_side))
    mapping.update(source_width=source_width, source_height=source_height, capture_max_side=capture_max_side)
    tensor = np.ascontiguousarray(canvas.transpose(2, 0, 1)[None], dtype=np.float32) / np.float32(255)
    return tensor, mapping


def espdl_score_threshold(scale: float, floor: float = 0.10) -> dict:
    """ESP32-S3 postprocessor quantizes its inverse-sigmoid cutoff first."""
    if not math.isfinite(scale) or scale <= 0 or not 0 < floor < 1:
        raise ValueError("Expected positive finite quantization scale and cutoff in (0,1)")
    probability = np.float32(floor)
    inverse_sigmoid = np.log(np.float32(probability / (np.float32(1) - probability)))
    scaled = np.float32(inverse_sigmoid * np.float32(1.0 / scale))
    integer = int(np.clip(np.floor(np.float32(scaled + np.float32(0.5))), -128, 127))
    logit = float(np.float32(integer) * np.float32(scale))
    return {"scale": scale, "integer_threshold": integer, "logit_threshold": logit,
            "effective_probability_floor": 1.0 / (1.0 + math.exp(-logit))}


def decode_espdet(outputs: dict[str, np.ndarray], mapping: dict, floor: float = 0.10,
                  nms_iou: float = 0.70, top_k: int = 10,
                  quantized_score_thresholds: dict | None = None) -> np.ndarray:
    """Return source-image XYXY/confidence with ESP-DL integer/inclusive NMS.

    The graph executor returns dequantized NCHW tensors. This is a host
    postprocessor simulation, not binary/hardware numerical verification.
    """
    candidates = []
    for stage, stride in enumerate((8, 16, 32)):
        side = 224 // stride
        boxes, logits = np.asarray(outputs[f"box{stage}"]), np.asarray(outputs[f"score{stage}"])
        if boxes.shape != (1, 4, side, side) or logits.shape != (1, 1, side, side):
            raise ValueError(f"Unexpected ESPDet stage-{stage} shapes: {boxes.shape}, {logits.shape}")
        if not np.isfinite(boxes).all() or not np.isfinite(logits).all():
            raise ValueError("Nonfinite ESPDet output")
        scores = 1.0 / (1.0 + np.exp(-np.clip(logits[0, 0].astype(np.float64), -80, 80)))
        eligible = (logits[0, 0] >= quantized_score_thresholds[f"score{stage}"]["logit_threshold"]
                    if quantized_score_thresholds is not None else scores >= floor)
        ys, xs = np.where(eligible)
        if not len(xs):
            continue
        distances = boxes[0, :, ys, xs].astype(np.float32)
        center_x = (xs * stride + stride // 2).astype(np.float32)
        center_y = (ys * stride + stride // 2).astype(np.float32)
        inverse_x, inverse_y = np.float32(mapping["inverse_x"]), np.float32(mapping["inverse_y"])
        source_boxes = np.stack(((center_x - distances[:, 0] * stride - mapping["left"]) * inverse_x,
                                 (center_y - distances[:, 1] * stride - mapping["top"]) * inverse_y,
                                 (center_x + distances[:, 2] * stride - mapping["left"]) * inverse_x,
                                 (center_y + distances[:, 3] * stride - mapping["top"]) * inverse_y), axis=1)
        # C++ casts source coordinates to int before NMS; preserve that order.
        candidates.append(np.column_stack((np.trunc(source_boxes), scores[ys, xs])))
    if not candidates:
        return np.empty((0, 5), dtype=np.float64)
    ordered = np.concatenate(candidates)
    ordered = ordered[np.argsort(-ordered[:, 4], kind="stable")]
    kept = []
    while len(ordered) and len(kept) < top_k:
        best = ordered[0]
        kept.append(best)
        others = ordered[1:]
        if not len(others):
            break
        intersection = np.maximum(np.minimum(best[2:4], others[:, 2:4]) - np.maximum(best[:2], others[:, :2]) + 1, 0).prod(1)
        area_best = (best[2] - best[0] + 1) * (best[3] - best[1] + 1)
        area_other = (others[:, 2] - others[:, 0] + 1) * (others[:, 3] - others[:, 1] + 1)
        union = area_best + area_other - intersection
        overlap = np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)
        ordered = others[overlap <= nms_iou]
    result = np.stack(kept)
    result[:, [0, 2]] = np.clip(result[:, [0, 2]], 0, mapping["width"] - 1)
    result[:, [1, 3]] = np.clip(result[:, [1, 3]], 0, mapping["height"] - 1)
    return result


def match_detections(predictions: np.ndarray, boxes: tuple, mapping: dict) -> np.ndarray:
    """Greedy IoU matching at .50:.05:.95 for one deer class."""
    correct = np.zeros((len(predictions), 10), dtype=bool)
    if not len(predictions) or not boxes:
        return correct
    normalized = np.asarray(boxes, dtype=np.float64)
    centers = normalized[:, :2] * [mapping["width"], mapping["height"]]
    halves = normalized[:, 2:] * [mapping["width"], mapping["height"]] / 2
    truth = np.column_stack((centers - halves, centers + halves))
    truth[:, [0, 2]] = np.clip(truth[:, [0, 2]], 0, mapping["width"])
    truth[:, [1, 3]] = np.clip(truth[:, [1, 3]], 0, mapping["height"])
    overlap = np.maximum(np.minimum(truth[:, None, 2:], predictions[None, :, 2:4]) -
                         np.maximum(truth[:, None, :2], predictions[None, :, :2]), 0).prod(2)
    truth_area = np.maximum(truth[:, 2:] - truth[:, :2], 0).prod(1)
    pred_area = np.maximum(predictions[:, 2:4] - predictions[:, :2], 0).prod(1)
    iou = overlap / np.maximum(truth_area[:, None] + pred_area[None, :] - overlap, 1e-12)
    for column, threshold in enumerate(np.linspace(0.5, 0.95, 10)):
        truth_ids, prediction_ids = np.where(iou >= threshold)
        order = np.argsort(-iou[truth_ids, prediction_ids], kind="stable")
        used_truth, used_predictions = set(), set()
        for position in order:
            truth_id, prediction_id = int(truth_ids[position]), int(prediction_ids[position])
            if truth_id not in used_truth and prediction_id not in used_predictions:
                correct[prediction_id, column] = True
                used_truth.add(truth_id)
                used_predictions.add(prediction_id)
    return correct
