"""Convert the public Kaggle deer archive to the folder layout used here."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path, PurePosixPath


def target_split_for(image_name: str) -> str:
    location = PurePosixPath(image_name).name.split("_im_", 1)[0]
    bucket = int(hashlib.sha1(location.encode("utf-8")).hexdigest()[:8], 16) % 5
    return "val" if bucket == 0 else "train"


def copy_split(archive: zipfile.ZipFile, source_split: str) -> dict[str, int]:
    image_prefix = f"Lila.v1.3k/{source_split}/images/"
    label_prefix = f"Lila.v1.3k/{source_split}/labels/"
    names = archive.namelist()
    images = [name for name in names if name.startswith(image_prefix) and name.lower().endswith(".jpg")]
    labels = {PurePosixPath(name).stem: name for name in names if name.startswith(label_prefix) and name.endswith(".txt")}
    if not images:
        raise SystemExit(f"No JPG images found under {image_prefix}; unexpected archive layout")

    counts = {"train": 0, "val": 0}
    for source_image in images:
        image_name = PurePosixPath(source_image).name
        target_split = target_split_for(image_name)
        label_name = PurePosixPath(source_image).stem
        if label_name not in labels:
            raise SystemExit(f"Missing deer annotation for {source_image}")
        image_dir = Path("images") / target_split
        label_dir = Path("labels") / target_split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        with archive.open(source_image) as src, (image_dir / image_name).open("wb") as dst:
            shutil.copyfileobj(src, dst)
        with archive.open(labels[label_name]) as src, (label_dir / f"{label_name}.txt").open("wb") as dst:
            shutil.copyfileobj(src, dst)
        counts[target_split] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Downloaded Kaggle deer-cameratraps ZIP")
    parser.add_argument("--out", type=Path, default=Path("datasets/deer"))
    args = parser.parse_args()
    if not args.archive.is_file():
        parser.error(f"archive not found: {args.archive}")
    # Resolve before changing directory: the documented CLI accepts a relative ZIP.
    archive_path = args.archive.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    import os

    previous = Path.cwd()
    try:
        os.chdir(args.out.resolve())
        with zipfile.ZipFile(archive_path) as archive:
            train_counts = copy_split(archive, "train")
            validation_counts = copy_split(archive, "valid")
    except zipfile.BadZipFile as error:
        raise SystemExit(f"invalid or incomplete ZIP file: {error}") from error
    finally:
        os.chdir(previous)

    (args.out / "deer.yaml").write_text(
        f"path: {args.out.resolve().as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n  0: deer\n"
    )
    train_count = train_counts["train"] + validation_counts["train"]
    validation_count = train_counts["val"] + validation_counts["val"]
    print(f"Prepared {train_count} training and {validation_count} validation deer images in {args.out}")
    print("Deer images are regrouped by camera location to keep locations out of both splits.")
    print("This source archive has no empty-scene negatives; add them before treating scores as product validation.")


if __name__ == "__main__":
    main()
