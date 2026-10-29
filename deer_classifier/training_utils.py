"""Small, dependency-free helpers for reproducible training and safe deployment."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def new_run_name() -> str:
    return datetime.now(timezone.utc).strftime("deer_%Y%m%d_%H%M%S_%f")


def validate_run_name(name: str) -> None:
    if not name or name in {".", ".."} or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in name):
        raise ValueError("--run-name must contain only letters, digits, underscores, and hyphens")


def validate_settings(size, epochs, batch, patience, workers, learning_rate, warmup_epochs, *,
                      warmup_bias_lr=0.0, mosaic=0.2, scale=0.25, cache="none", close_mosaic=10) -> None:
    if any(value <= 0 or value % 32 for value in size):
        raise ValueError("--size dimensions must be positive multiples of 32")
    if epochs < 1 or batch < 1 or patience < 0 or workers < 0:
        raise ValueError("epochs/batch must be positive; patience/workers must be nonnegative")
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("--learning-rate must be finite and positive")
    if not math.isfinite(warmup_epochs) or warmup_epochs < 0:
        raise ValueError("--warmup-epochs must be finite and nonnegative")
    if not math.isfinite(warmup_bias_lr) or warmup_bias_lr < 0:
        raise ValueError("--warmup-bias-lr must be finite and nonnegative")
    for option, value in (("--mosaic", mosaic), ("--scale", scale)):
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{option} must be finite and in [0, 1]")
    if close_mosaic < 0:
        raise ValueError("--close-mosaic must be nonnegative")
    if cache not in {"none", "ram", "disk"}:
        raise ValueError("--cache must be none, ram, or disk")


def select_device(requested: str, torch_module=None) -> str:
    """Resolve on the training interpreter, not the wrapper's Python process."""
    if requested != "auto":
        return requested
    if torch_module is None:
        import torch as torch_module
    if torch_module.cuda.is_available():
        return "0"
    mps = getattr(torch_module.backends, "mps", None)
    return "mps" if mps is not None and mps.is_available() else "cpu"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def provenance(repo: Path, checkpoint: Path, settings: dict) -> dict:
    try:
        revision = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                  check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    packages = {}
    for name in ("torch", "torchvision", "ultralytics", "onnx", "onnxruntime", "esp-ppq"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "esp_detection_revision": revision,
        "packages": packages,
        "pretrained_checkpoint": str(checkpoint),
        "pretrained_sha256": sha256(checkpoint),
        "settings": settings,
    }


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def deploy_model(source: Path, output: Path, *, overwrite: bool = False) -> dict:
    """Publish only a completed export. Failure leaves the previous model intact."""
    if not source.is_file() or source.stat().st_size == 0:
        raise ValueError(f"quantizer did not produce a nonempty ESP-DL model: {source}")
    if output.exists() and not overwrite:
        raise FileExistsError(f"model already exists: {output}; choose a candidate path or --overwrite-output")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".espdl.tmp", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        shutil.copyfile(source, temporary)
        if overwrite:
            os.replace(temporary, output)
        else:
            # An exclusive link also protects an output created while training ran.
            os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(output), "size_bytes": output.stat().st_size, "sha256": sha256(output)}
