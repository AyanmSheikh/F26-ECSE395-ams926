"""Dependency-free metrics for the deployed max-deer-box score contract.

Image-presence counts do not require box overlap; report detector mAP separately.
Unordered still images cannot establish the behavior of a temporal gate.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_deer_label(path: Path) -> bool:
    """Require an explicit empty label for negatives, never infer from absence."""
    return bool(read_deer_boxes(path))


def read_deer_boxes(path: Path) -> list[tuple[float, float, float, float]]:
    """Read normalized XYWH boxes, rejecting unknown classes and bad labels."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing label (use an empty file for a confirmed negative): {path}")
    boxes = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"{path}:{number}: expected class x_center y_center width height")
        try:
            class_id, x, y, width, height = map(float, fields)
        except ValueError as error:
            raise ValueError(f"{path}:{number}: non-numeric YOLO label") from error
        if class_id != 0 or not all(math.isfinite(value) for value in (x, y, width, height)):
            raise ValueError(f"{path}:{number}: expected finite boxes of class 0 = deer")
        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < width <= 1 and 0 < height <= 1):
            raise ValueError(f"{path}:{number}: invalid normalized deer box")
        boxes.append((x, y, width, height))
    return boxes


def summarize_presence(rows: list[dict], thresholds: list[float]) -> list[dict]:
    """Return threshold confusion counts; undefined ratios are JSON null."""
    if not rows:
        raise ValueError("No images were evaluated")
    seen = set()
    for row in rows:
        if row["image"] in seen:
            raise ValueError(f"Image evaluated more than once: {row['image']}")
        seen.add(row["image"])
        if type(row["has_deer"]) is not bool:
            raise ValueError("has_deer must be a boolean")
        if not math.isfinite(row["score"]) or not 0 <= row["score"] <= 1:
            raise ValueError(f"Invalid confidence for {row['image']}: {row['score']}")

    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None

    summaries = []
    for threshold in thresholds:
        if not math.isfinite(threshold) or not 0 < threshold <= 1:
            raise ValueError("Confidence thresholds must be in (0, 1]")
        tp = fp = tn = fn = 0
        for row in rows:
            predicted = row["score"] >= threshold
            if row["has_deer"]:
                tp += predicted
                fn += not predicted
            else:
                fp += predicted
                tn += not predicted
        summaries.append({
            "threshold": threshold,
            "true_positive": tp, "false_positive": fp,
            "true_negative": tn, "false_negative": fn,
            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
            "false_positive_rate": ratio(fp, fp + tn),
            "missed_deer_rate": ratio(fn, tp + fn),
            "accuracy": ratio(tp + tn, len(rows)),
            "specificity": ratio(tn, tn + fp),
            "balanced_accuracy": ((tp / (tp + fn) + tn / (tn + fp)) / 2
                                  if tp + fn and tn + fp else None),
        })
    return summaries
