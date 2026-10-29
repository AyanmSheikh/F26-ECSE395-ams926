"""Reconstruct location-held-out validation images from public sources anonymously.

Kaggle ZIP entries are fetched with verified HTTP byte ranges, avoiding the full
4.6 GB archive. Idaho negatives reproduce fetch_negatives.py's deterministic
sequence/category sampler. No training images are downloaded.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import time
import urllib.error
import urllib.request
import zipfile
import zlib

from fetch_negatives import BASE_URL, NEGATIVE_CATEGORIES, UNCERTAIN_CATEGORIES, stable_bucket
from prepare_dataset import target_split_for

KAGGLE_URL = "https://www.kaggle.com/api/v1/datasets/download/winnerbishal/deer-cameratraps?datasetVersionNumber=2"
METADATA_URL = "https://storage.googleapis.com/public-datasets-lila/idaho-camera-traps/idaho-camera-traps.json.zip"
USER_AGENT = "deer-classifier-validation-recovery/1.0"


class HTTPRangeFile(io.RawIOBase):
    """Seekable, bounded range reader accepted by stdlib zipfile, including ZIP64."""

    def __init__(self, url: str, opener=urllib.request.urlopen, block_size=65536):
        super().__init__()
        self.url = url
        self.opener = opener
        self.block_size = block_size
        self.position = 0
        self.cache = OrderedDict()
        self.bytes_downloaded = 0
        self.requests = 0
        self.length = None
        self._request(0, 0)

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        if whence not in (io.SEEK_SET, io.SEEK_CUR, io.SEEK_END):
            raise ValueError("invalid seek mode")
        position = offset if whence == io.SEEK_SET else self.position + offset if whence == io.SEEK_CUR else self.length + offset
        if position < 0:
            raise ValueError("negative seek")
        self.position = position
        return position

    def _request(self, start, end):
        expected = end - start + 1
        request = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}", "User-Agent": USER_AGENT})
        for attempt in range(4):
            try:
                with self.opener(request, timeout=90) as response:
                    content_range = response.headers.get("Content-Range", "")
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
                    if response.status != 206 or not match or tuple(map(int, match.groups()[:2])) != (start, end):
                        raise ValueError(f"server did not honor byte range {start}-{end}: status={response.status}, {content_range!r}")
                    total = int(match.group(3))
                    if self.length is not None and self.length != total:
                        raise ValueError("remote ZIP changed size during recovery")
                    self.length = total
                    payload = response.read(expected + 1)
                    if len(payload) != expected:
                        raise OSError(f"incomplete byte range: expected {expected}, received {len(payload)}")
                    self.bytes_downloaded += len(payload)
                    self.requests += 1
                    return payload
            except (OSError, urllib.error.URLError):
                if attempt == 3:
                    raise
                time.sleep(attempt + 1)

    def read(self, size=-1):
        size = min(self.length - self.position, size if size >= 0 else self.length - self.position)
        if size <= 0:
            return b""
        if size > 32 * 1024 * 1024:
            raise ValueError("refusing a range larger than 32 MiB; this reader must not fetch the entire ZIP")
        if size > self.block_size:
            result = self._request(self.position, self.position + size - 1)
        else:
            first = self.position // self.block_size
            last = (self.position + size - 1) // self.block_size
            blocks = []
            for index in range(first, last + 1):
                if index not in self.cache:
                    start = index * self.block_size
                    self.cache[index] = self._request(start, min(start + self.block_size, self.length) - 1)
                    while len(self.cache) > 16:
                        self.cache.popitem(last=False)
                self.cache.move_to_end(index)
                blocks.append(self.cache[index])
            offset = self.position - first * self.block_size
            result = b"".join(blocks)[offset:offset + size]
        self.position += len(result)
        return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def save_bytes(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"refusing to overwrite a different existing sample: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_bytes(payload)
    temporary.replace(path)


def download(url, limit):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read(limit + 1)
                if len(payload) > limit:
                    raise ValueError(f"download exceeded {limit} bytes: {url}")
                return payload
        except (OSError, urllib.error.URLError):
            if attempt == 3:
                raise
            time.sleep(attempt + 1)


def positive_members(archive):
    names = set(archive.namelist())
    selected = []
    for name in sorted(names):
        parts = PurePosixPath(name).parts
        if len(parts) != 4 or parts[:1] != ("Lila.v1.3k",) or parts[1] not in {"train", "valid"} or parts[2] != "images" or not name.lower().endswith(".jpg"):
            continue
        if target_split_for(name) != "val":
            continue
        label = f"Lila.v1.3k/{parts[1]}/labels/{PurePosixPath(name).stem}.txt"
        if label not in names:
            raise ValueError(f"missing positive label in ZIP: {name}")
        selected.append((name, label))
    if not selected:
        raise ValueError("no held-out deer images found; unexpected source archive")
    basenames = [PurePosixPath(image).name for image, _ in selected]
    if len(set(basenames)) != len(basenames):
        raise ValueError("duplicate held-out image basenames")
    return selected


def negative_samples(metadata, count):
    """Same iteration order, first frame per sequence and round robin as fetch_negatives."""
    categories = {entry["id"]: entry["name"].lower() for entry in metadata["categories"]}
    image_by_id = {entry["id"]: entry for entry in metadata["images"]}
    sequence_categories = {}
    for annotation in metadata["annotations"]:
        image = image_by_id.get(annotation["image_id"])
        if image is not None:
            sequence_categories.setdefault(image["seq_id"], set()).add(categories.get(annotation["category_id"], "unknown"))
    seen, candidates = set(), {}
    for image in metadata["images"]:
        sequence = image["seq_id"]
        if sequence in seen:
            continue
        seen.add(sequence)
        labels = sequence_categories.get(sequence, set())
        eligible = sorted(labels & NEGATIVE_CATEGORIES)
        if not labels or labels & UNCERTAIN_CATEGORIES or not eligible:
            continue
        if stable_bucket(PurePosixPath(image["file_name"]).parts[0]) != 0:
            continue
        candidates.setdefault(eligible[0], []).append({"source_path": image["file_name"], "sequence": sequence, "category": eligible[0]})
    category_order = sorted(candidates)
    selected, offset = [], 0
    while len(selected) < count and category_order:
        category = category_order[offset % len(category_order)]
        index = offset // len(category_order)
        if index < len(candidates[category]):
            selected.append(candidates[category][index])
        elif all(index >= len(candidates[name]) for name in category_order):
            break
        offset += 1
    if len(selected) != count:
        raise ValueError(f"only {len(selected)} eligible held-out negatives, requested {count}")
    return selected


def recover_positive(archive, pair, dataset):
    source_image, source_label = pair
    label = archive.read(source_label)
    if not label.strip():
        raise ValueError(f"expected annotated positive: {source_label}")
    for line in label.decode("utf-8").splitlines():
        values = line.split()
        if len(values) != 5 or values[0] != "0" or any(not 0 <= float(v) <= 1 for v in values[1:]):
            raise ValueError(f"unexpected YOLO deer label: {source_label}")
    image_path = dataset / "images/val" / PurePosixPath(source_image).name
    image = image_path.read_bytes() if image_path.is_file() else archive.read(source_image)
    if not image.startswith(b"\xff\xd8"):
        raise ValueError(f"invalid JPEG marker: {source_image}")
    if zlib.crc32(image) != archive.getinfo(source_image).CRC:
        raise ValueError(f"image does not match the source ZIP checksum: {image_path}")
    save_bytes(image_path, image)
    save_bytes(dataset / "labels/val" / PurePosixPath(source_label).name, label)
    return {"image": image_path.name, "label": "deer", "source_member": source_image, "sha256": digest(image), "label_sha256": digest(label)}


def recover_negative(sample, dataset):
    image_path = dataset / "images/val" / PurePosixPath(sample["source_path"]).name
    label_path = dataset / "labels/val" / f"{image_path.stem}.txt"
    if label_path.is_file() and label_path.read_bytes().strip():
        raise ValueError(f"negative would conflict with a deer label: {label_path}")
    image = image_path.read_bytes() if image_path.is_file() else download(BASE_URL + sample["source_path"], 16 * 1024 * 1024)
    if not image.startswith(b"\xff\xd8"):
        raise ValueError(f"invalid negative JPEG marker: {sample['source_path']}")
    save_bytes(image_path, image)
    save_bytes(label_path, b"")
    return {"image": image_path.name, "label": "no_deer", **sample, "sha256": digest(image)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).parent / "datasets/deer")
    parser.add_argument("--positive-limit", type=int, help="Only for an initial subset; omitted means all held-out deer")
    parser.add_argument("--negative-count", type=int, default=150)
    parser.add_argument("--initial-batch", type=int, default=10)
    parser.add_argument("--plan-only", action="store_true", help="Read ZIP directory and print counts/bytes without downloading images or metadata")
    args = parser.parse_args()
    if (args.positive_limit is not None and args.positive_limit < 1) or args.negative_count < 0 or args.initial_batch < 1:
        parser.error("counts must be nonnegative and positive-limit/initial-batch must be positive")
    dataset = args.dataset.resolve()
    dataset.mkdir(parents=True, exist_ok=True)
    with HTTPRangeFile(KAGGLE_URL) as remote, zipfile.ZipFile(remote) as archive:
        positives = positive_members(archive)
        available_positive_count = len(positives)
        if args.positive_limit is not None:
            positives = positives[:args.positive_limit]
        estimated_bytes = sum(archive.getinfo(name).compress_size for pair in positives for name in pair)
        print(json.dumps({"heldout_deer_available": available_positive_count, "deer_to_recover": len(positives), "negative_count": args.negative_count,
                          "selected_positive_compressed_bytes": estimated_bytes, "full_archive_bytes": remote.length,
                          "directory_bytes_downloaded": remote.bytes_downloaded}), flush=True)
        if args.plan_only:
            return
        metadata_sha256, negatives = None, []
        if args.negative_count:
            metadata_path = dataset / "recovery/idaho-camera-traps.json.zip"
            if not metadata_path.is_file():
                save_bytes(metadata_path, download(METADATA_URL, 64 * 1024 * 1024))
            with zipfile.ZipFile(metadata_path) as source:
                json_name = next(name for name in source.namelist() if name.endswith(".json"))
                with source.open(json_name) as stream:
                    metadata = json.load(stream)
            negatives = negative_samples(metadata, args.negative_count)
            del metadata
            metadata_sha256 = digest(metadata_path.read_bytes())
        manifest = {"status": "recovering", "kaggle_url": KAGGLE_URL, "archive_bytes": remote.length,
                    "reconstruction_limit": "Reconstructed from current preparation code; not verified against the original training manifest or original 602-image validation set",
                    "positive_split_rule": "prepare_dataset.target_split_for; source train+valid; camera SHA1 mod5==0",
                    "available_positive_count": available_positive_count, "requested_positive_count": len(positives),
                    "negative_metadata_url": METADATA_URL, "negative_metadata_sha256": metadata_sha256,
                    "negative_sampler": "fetch_negatives.py deterministic first frame per sequence and category round robin; val only",
                    "negative_label_limit": "Source species labels are sequence-level, not verified per-frame absence of deer",
                    "requested_negative_count": len(negatives), "samples": []}
        path = dataset / "recovery_manifest.json"
        positive_initial = min(args.initial_batch, len(positives))
        negative_initial = min(args.initial_batch, len(negatives))
        for pair in positives[:positive_initial]:
            manifest["samples"].append(recover_positive(archive, pair, dataset))
        for sample in negatives[:negative_initial]:
            manifest["samples"].append(recover_negative(sample, dataset))
        write_json(path, manifest)
        write_json(dataset / "recovery_initial_ready.json", {"positive_count": positive_initial, "negative_count": negative_initial,
                                                            "images": [sample["image"] for sample in manifest["samples"]]})
        print(f"INITIAL_READY: {positive_initial} deer + {negative_initial} negatives in {dataset}", flush=True)
        for index, pair in enumerate(positives[positive_initial:], positive_initial + 1):
            manifest["samples"].append(recover_positive(archive, pair, dataset))
            if index % 25 == 0:
                write_json(path, manifest)
                print(f"Recovered deer {index}/{len(positives)}; ZIP bytes downloaded {remote.bytes_downloaded}", flush=True)
        for index, sample in enumerate(negatives[negative_initial:], negative_initial + 1):
            manifest["samples"].append(recover_negative(sample, dataset))
            if index % 25 == 0:
                write_json(path, manifest)
                print(f"Recovered negatives {index}/{len(negatives)}", flush=True)
        manifest.update(status="complete", positive_count=len(positives), negative_count=len(negatives),
                        kaggle_bytes_downloaded=remote.bytes_downloaded, kaggle_range_requests=remote.requests)
        write_json(path, manifest)
        save_bytes(dataset / "deer.yaml", (f"path: {json.dumps(dataset.as_posix())}\nval: images/val\nnames:\n  0: deer\n").encode("utf-8"))
        print(f"COMPLETE: {len(positives)} deer + {len(negatives)} negatives; manifest={path}", flush=True)


if __name__ == "__main__":
    main()
