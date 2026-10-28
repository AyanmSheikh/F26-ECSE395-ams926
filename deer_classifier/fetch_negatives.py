"""Add public Idaho camera-trap non-deer scenes as YOLO empty-label images."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_URL = "https://storage.googleapis.com/public-datasets-lila/idaho-camera-traps/public/"
NEGATIVE_CATEGORIES = {
    "empty", "bird", "squirrel", "fox", "coyote", "elk", "moose",
    "cattle", "raccoon", "skunk", "bear", "lagomorph", "grouse", "turkey",
}
UNCERTAIN_CATEGORIES = {"deer", "unknown cervid", "unknown ungulate"}


def stable_bucket(value: str) -> int:
    return int(hashlib.sha1(value.encode("utf-8")).hexdigest()[:8], 16) % 5


def fetch_one(item: tuple[str, str, Path]) -> tuple[str, bool, str | None]:
    file_name, split, root = item
    image_name = Path(file_name).name
    image_dir = root / "images" / split
    label_dir = root / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / image_name
    label_path = label_dir / f"{image_path.stem}.txt"
    if image_path.exists():
        label_path.touch(exist_ok=True)
        return split, True, None

    request = urllib.request.Request(BASE_URL + file_name, headers={"User-Agent": "deer-classifier-data-prep/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response, image_path.open("wb") as output:
                output.write(response.read())
            label_path.touch()
            return split, True, None
        except (OSError, urllib.error.URLError) as error:
            image_path.unlink(missing_ok=True)
            if attempt == 2:
                return split, False, f"{file_name}: {error}"
            time.sleep(attempt + 1)
    return split, False, f"{file_name}: retries exhausted"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata_zip", type=Path, help="Official Idaho Camera Traps metadata ZIP")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/deer"))
    parser.add_argument("--train-count", type=int, default=600)
    parser.add_argument("--validation-count", type=int, default=150)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not args.metadata_zip.is_file():
        parser.error(f"metadata ZIP not found: {args.metadata_zip}")

    with zipfile.ZipFile(args.metadata_zip) as archive:
        json_name = next((name for name in archive.namelist() if name.endswith(".json")), None)
        if json_name is None:
            parser.error("metadata ZIP does not contain a JSON file")
        with archive.open(json_name) as stream:
            metadata = json.load(stream)

    categories = {entry["id"]: entry["name"].lower() for entry in metadata["categories"]}
    image_by_id = {entry["id"]: entry for entry in metadata["images"]}
    sequence_categories: dict[str, set[str]] = {}
    for annotation in metadata["annotations"]:
        image = image_by_id.get(annotation["image_id"])
        if image is not None:
            sequence_categories.setdefault(image["seq_id"], set()).add(
                categories.get(annotation["category_id"], "unknown")
            )

    by_split_and_category: dict[tuple[str, str], list[tuple[str, str]]] = {}
    seen_sequences: set[str] = set()
    for image in metadata["images"]:
        sequence = image["seq_id"]
        if sequence in seen_sequences:
            continue
        seen_sequences.add(sequence)
        labels = sequence_categories.get(sequence, set())
        if not labels or labels & UNCERTAIN_CATEGORIES:
            continue
        eligible = sorted(labels & NEGATIVE_CATEGORIES)
        if not eligible:
            continue
        location = Path(image["file_name"]).parts[0]
        # Hold out entire camera locations to reduce train/validation leakage.
        split = "val" if stable_bucket(location) == 0 else "train"
        by_split_and_category.setdefault((split, eligible[0]), []).append((image["file_name"], sequence))

    requests: list[tuple[str, str, Path]] = []
    for split, count in (("train", args.train_count), ("val", args.validation_count)):
        categories_present = sorted(category for candidate_split, category in by_split_and_category if candidate_split == split)
        if not categories_present:
            parser.error(f"No eligible negative images in {split} split")
        selected: list[str] = []
        offset = 0
        while len(selected) < count:
            category = categories_present[offset % len(categories_present)]
            candidates = by_split_and_category[(split, category)]
            round_index = offset // len(categories_present)
            if round_index < len(candidates):
                selected.append(candidates[round_index][0])
            elif all(offset // len(categories_present) >= len(by_split_and_category[(split, name)])
                     for name in categories_present):
                break
            offset += 1
        requests.extend((file_name, split, args.dataset) for file_name in selected)

    failures: list[str] = []
    completed = {"train": 0, "val": 0}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(fetch_one, request) for request in requests]
        for future in as_completed(futures):
            split, success, error = future.result()
            completed[split] += int(success)
            if error:
                failures.append(error)
    print(f"Added {completed['train']} training and {completed['val']} validation empty-label hard negatives.")
    if failures:
        raise SystemExit("Some downloads failed:\n" + "\n".join(failures[:20]))


if __name__ == "__main__":
    main()
