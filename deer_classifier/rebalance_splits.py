"""Regroup paired YOLO images/labels by camera location into train and val."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def destination(image: Path) -> str:
    location = image.name.split("_im_", 1)[0]
    bucket = int(hashlib.sha1(location.encode("utf-8")).hexdigest()[:8], 16) % 5
    return "val" if bucket == 0 else "train"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, default=Path("datasets/deer"))
    args = parser.parse_args()
    root = args.dataset
    moves = []
    for source_split in ("train", "val"):
        for image in (root / "images" / source_split).glob("*.jpg"):
            label = root / "labels" / source_split / f"{image.stem}.txt"
            if not label.is_file():
                raise SystemExit(f"missing YOLO label for {image}")
            target_split = destination(image)
            if target_split != source_split:
                moves.append((image, label, target_split))

    for image, label, target_split in moves:
        target_image = root / "images" / target_split / image.name
        target_label = root / "labels" / target_split / label.name
        if target_image.exists() or target_label.exists():
            raise SystemExit(f"refusing to overwrite existing sample {image.name}")
        image.replace(target_image)
        label.replace(target_label)
    print(f"Moved {len(moves)} image/label pairs so each camera location is in one split.")


if __name__ == "__main__":
    main()
