"""Small compatibility bridge for Espressif ESP-Detection and Ultralytics."""

from __future__ import annotations

import sys
import copy
from pathlib import Path


def restore_sppf_activations(target_model, source_model) -> int:
    """Preserve parameter-free SPPF activations omitted from state dictionaries.

    Recent Ultralytics constructs SPPF.cv1 without activation; legacy ESPDet cat
    checkpoints use ReLU there. Deer checkpoints already trained with Identity
    must retain Identity. Copy the source block rather than imposing either one.
    """
    target_modules = dict(target_model.named_modules())
    restored = 0
    for name, source in source_model.named_modules():
        target = target_modules.get(name)
        if (source.__class__.__name__ == "SPPF" and target is not None
                and target.__class__.__name__ == "SPPF"
                and hasattr(getattr(source, "cv1", None), "act")
                and hasattr(getattr(target, "cv1", None), "act")):
            target.cv1.act = copy.deepcopy(source.cv1.act)
            restored += 1
    return restored


def load_esp_detection(repo: Path):
    """Import ESP-Detection and normalize two recent Ultralytics API changes."""
    sys.path.insert(0, str(repo.resolve()))
    import train as upstream_train
    import deploy.export as upstream_export
    import deploy.quantize as upstream_quantize

    # ESPDetect uses DSConv in its box head, while recent Ultralytics checkpoint
    # loading assumes every detection-head layer exposes Conv.conv. Both source
    # and target models here have one class, so copy only matching state tensors.
    from ultralytics.nn.tasks import BaseModel
    from ultralytics.utils import LOGGER
    from ultralytics.utils.torch_utils import intersect_dicts
    import ultralytics.utils.nms as upstream_nms

    def load_matching_espdet_weights(self, weights, verbose=True):
        source_model = (weights.get("ema") or weights["model"]) if isinstance(weights, dict) else weights
        source_state = source_model.float().state_dict()
        compatible = intersect_dicts(source_state, self.state_dict())
        self.load_state_dict(compatible, strict=False)
        restored = restore_sppf_activations(self, source_model)
        if verbose:
            LOGGER.info(
                f"Transferred {len(compatible)}/{len(self.state_dict())} "
                f"shape-compatible checkpoint tensors; preserved {restored} source SPPF activations"
            )

    BaseModel.load = load_matching_espdet_weights

    # Ultralytics' default validation NMS budget can be too short for a 32-image
    # batch on this host, causing some predictions to be omitted from metrics.
    nms = upstream_nms.non_max_suppression
    if not getattr(nms, "_deer_extended_budget", False):
        def nms_with_host_budget(*args, **kwargs):
            kwargs["max_time_img"] = max(kwargs.get("max_time_img", 0.05), 0.5)
            return nms(*args, **kwargs)

        nms_with_host_budget._deer_extended_budget = True
        upstream_nms.non_max_suppression = nms_with_host_budget

    # ESP-PPQ's full per-layer quantization-error report adds many redundant
    # inference passes and does not change the emitted model or calibration.
    quantizer = upstream_quantize.espdl_quantize_onnx
    if not getattr(quantizer, "_deer_skip_error_report", False):
        def quantize_without_error_report(*args, **kwargs):
            kwargs["error_report"] = False
            return quantizer(*args, **kwargs)

        quantize_without_error_report._deer_skip_error_report = True
        upstream_quantize.espdl_quantize_onnx = quantize_without_error_report

    # ESP-Detection's exporter returns (path, ONNX model), while recent
    # Ultralytics Exporter.__call__ expects the export method to return a path.
    exporter = upstream_export.ESP_Detect_Exporter
    if not getattr(exporter.export_onnx, "_deer_returns_path", False):
        original_export_onnx = exporter.export_onnx

        def export_onnx_path(self, *args, **kwargs):
            result = original_export_onnx(self, *args, **kwargs)
            return result[0] if isinstance(result, tuple) else result

        export_onnx_path._deer_returns_path = True
        exporter.export_onnx = export_onnx_path

    return upstream_train.Train, upstream_export.Export, upstream_quantize.quant_espdet
