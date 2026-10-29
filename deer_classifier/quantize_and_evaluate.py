"""Export an ESP32-S3 int8 candidate and evaluate its supported PPQ CPU graph.

The .espdl binary is associated by provenance, not executed by this host script.
On-board golden-vector and camera tests remain necessary before deployment.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import time

from espdet_compat import load_esp_detection
from image_metrics import sha256_file, summarize_presence
from quantization_support import (OUTPUT_NAMES, assert_disjoint, collect_split, decode_espdet,
                                  espdl_score_threshold, manifest_hash, match_detections,
                                  prepare_image, resolve_capture_max_side, select_calibration)
from training_utils import provenance, write_json


def artifact(path: Path) -> dict:
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esp-detection", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--native-graph", type=Path, help="Re-evaluate a graph produced by this script without recalibration")
    parser.add_argument("--onnx-reference", type=Path, help="Reuse a verified export from the identical checkpoint for a controlled preprocessing comparison")
    parser.add_argument("--dataset", type=Path, required=True, help="YOLO root with images/train,val and labels/train,val")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory; existing directories are never overwritten")
    parser.add_argument("--calibration-steps", type=int, default=32)
    parser.add_argument("--calibration-batch-size", type=int, default=8)
    parser.add_argument("--equalization-iterations", type=int, default=4)
    parser.add_argument("--seed", type=int, default=395)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--capture-max-side", type=int, default=None,
                        help="Bilinear acquisition proxy max side: new exports default 320; 0 is raw legacy; native evaluation uses its saved setting")
    parser.add_argument("--thresholds", type=float, nargs="+", default=(0.10, 0.25, 0.50, 0.70, 0.85, 0.95))
    parser.add_argument("--max-model-bytes", type=int, default=768000, help="750 KiB including embedded golden tensors")
    parser.add_argument("--max-parameters", type=int, default=400000)
    parser.add_argument("--skip-box-metrics", action="store_true")
    parser.add_argument("--skip-evaluation", action="store_true", help="Export artifacts now; evaluate --native-graph later")
    args = parser.parse_args()
    if bool(args.checkpoint) == bool(args.native_graph):
        parser.error("Provide exactly one of --checkpoint or --native-graph")
    if args.native_graph and args.onnx_reference:
        parser.error("--onnx-reference applies only to a new --checkpoint export")
    if args.checkpoint and (not args.esp_detection or not (args.esp_detection / "train.py").is_file()):
        parser.error("Export requires a valid --esp-detection checkout")
    if args.calibration_steps < 8 or args.calibration_batch_size < 1 or args.equalization_iterations < 0:
        parser.error("Require calibration steps >= 8, batch size >= 1, and nonnegative equalization iterations")
    if args.threads < 1 or args.max_model_bytes < 1 or args.max_parameters < 1:
        parser.error("Thread count and artifact budgets must be positive")
    if any(not 0.10 <= threshold <= 1 for threshold in args.thresholds):
        parser.error("Thresholds must be finite and within [0.10, 1]")
    prior = None
    if args.native_graph:
        prior = json.loads((args.native_graph.resolve().parent / "quantization_manifest.json").read_text(encoding="utf-8"))
    try:
        args.capture_max_side = resolve_capture_max_side(args.capture_max_side, prior["settings"] if prior else None)
    except ValueError as error:
        parser.error(str(error))
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        parser.error(f"Output directory already exists: {output_dir}")
    dataset = args.dataset.resolve()
    train, validation = collect_split(dataset, "train"), collect_split(dataset, "val")
    assert_disjoint(train, validation)
    print(f"Audited {len(train)} train / {len(validation)} validation images; no image-content overlap", flush=True)

    import numpy as np
    os.environ["OMP_NUM_THREADS"] = str(args.threads)
    os.environ["MKL_NUM_THREADS"] = str(args.threads)
    import torch
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    from esp_ppq import TargetPlatform
    from esp_ppq.api import (QuantizationSettingFactory, espdl_quantize_onnx,
                             export_ppq_graph, load_native_graph)
    from esp_ppq.executor import TorchExecutor
    import onnxruntime as ort

    runtime_packages = {}
    for package in ("torch", "esp-ppq", "onnxruntime", "ultralytics", "numpy", "Pillow"):
        try:
            runtime_packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            runtime_packages[package] = None

    output_dir.mkdir(parents=True)
    manifest_path = output_dir / "quantization_manifest.json"
    manifest = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "preparing", "scope": "ESP-PPQ CPU int8 quantization simulation; not .espdl binary or board execution",
                "runtime_packages": runtime_packages,
                "dataset": {"path": str(dataset), "train_images": len(train), "validation_images": len(validation),
                            "train_manifest_sha256": manifest_hash(train), "validation_manifest_sha256": manifest_hash(validation)},
                "settings": {"target": "esp32s3", "bits": 8, "input_shape_nchw": [1, 3, 224, 224],
                             "preprocessing": "RGB /255; ESP-DL float32 centered letterbox114; floor-index nearest neighbor",
                             "capture_max_side": args.capture_max_side,
                             "acquisition_proxy": ("Aspect-preserving Pillow BILINEAR downsample before ESP-DL preprocessing; no upsample/crop; not exact OV5640 ISP/JPEG"
                                                   if args.capture_max_side else "None: legacy original-resolution RGB directly into ESP-DL preprocessing"),
                             "detection_coordinate_space": "Captured/proxy RGB pixel coordinates; YOLO labels stay normalized",
                             "score_floor": 0.10, "nms_iou": 0.70, "max_detections": 10,
                             "thresholds": list(args.thresholds), "threads": args.threads,
                             "max_model_bytes": args.max_model_bytes, "max_parameters": args.max_parameters},
                "implementation": {"script_sha256": sha256_file(Path(__file__)),
                                   "preprocessing_sha256": sha256_file(Path(__file__).with_name("quantization_support.py"))}}
    try:
        if args.checkpoint:
            checkpoint = args.checkpoint.resolve()
            if not checkpoint.is_file():
                raise FileNotFoundError(checkpoint)
            _, export_model, _ = load_esp_detection(args.esp_detection.resolve())
            from ultralytics import YOLO
            source = YOLO(str(checkpoint))
            if len(source.names) != 1 or str(source.names[0]).lower() != "deer":
                raise ValueError(f"Expected class 0 = deer; got {source.names}")
            parameter_count = sum(parameter.numel() for parameter in source.model.parameters())
            if parameter_count > args.max_parameters:
                raise ValueError(f"Checkpoint has {parameter_count} parameters, over budget {args.max_parameters}")
            del source
            selected = select_calibration(train, args.calibration_steps * args.calibration_batch_size, args.seed)
            manifest.update(provenance(args.esp_detection.resolve(), checkpoint, manifest["settings"]))
            manifest["parameter_count"] = parameter_count
            manifest["class_names"] = {"0": "deer"}
            manifest["calibration"] = {"source_split": "train only", "seed": args.seed,
                                       "steps": args.calibration_steps, "batch_size": args.calibration_batch_size,
                                       "equalization_iterations": args.equalization_iterations,
                                       "deer_images": sum(sample.positive for sample in selected),
                                       "negative_images": sum(not sample.positive for sample in selected),
                                       "images": [{"image": str(sample.image), "sha256": sample.image_hash,
                                                   "label_sha256": sample.label_hash} for sample in selected]}
            write_json(manifest_path, manifest)
            local_checkpoint = output_dir / "source.pt"
            shutil.copyfile(checkpoint, local_checkpoint)
            if sha256_file(local_checkpoint) != manifest["pretrained_sha256"]:
                raise RuntimeError("Checkpoint changed while snapshotting; use an immutable saved checkpoint")
            onnx_path = local_checkpoint.with_suffix(".onnx")
            if args.onnx_reference:
                reference_path = args.onnx_reference.resolve()
                reference_manifest_path = reference_path.parent / "quantization_manifest.json"
                reference_manifest = json.loads(reference_manifest_path.read_text(encoding="utf-8"))
                if sha256_file(reference_path) != reference_manifest["artifacts"]["onnx"]["sha256"]:
                    raise ValueError("Requested ONNX reference differs from its recorded export hash")
                if reference_manifest["artifacts"]["checkpoint"]["sha256"] != manifest["pretrained_sha256"]:
                    raise ValueError("Requested ONNX reference came from a different checkpoint")
                shutil.copyfile(reference_path, onnx_path)
                manifest["reused_float_reference"] = {"onnx": artifact(reference_path), "manifest": artifact(reference_manifest_path)}
            else:
                export_model(str(local_checkpoint), [224, 224])
            quantization_onnx = output_dir / "quantization_input.onnx"
            shutil.copyfile(onnx_path, quantization_onnx)
            model_path, native_path = output_dir / "deer_candidate.espdl", output_dir / "deer_candidate.native"

            class CalibrationDataset(torch.utils.data.Dataset):
                def __len__(self):
                    return len(selected)

                def __getitem__(self, index):
                    tensor, _ = prepare_image(selected[index].image, args.capture_max_side)
                    return torch.from_numpy(tensor[0])

            loader = torch.utils.data.DataLoader(CalibrationDataset(), batch_size=args.calibration_batch_size,
                                                shuffle=False, num_workers=0)
            settings = QuantizationSettingFactory.espdl_setting()
            settings.equalization = args.equalization_iterations > 0
            settings.equalization_setting.iterations = args.equalization_iterations
            settings.equalization_setting.value_threshold = 0.4
            settings.equalization_setting.opt_level = 2
            golden_input = torch.from_numpy(prepare_image(selected[0].image, args.capture_max_side)[0])
            manifest["status"] = "quantizing"
            write_json(manifest_path, manifest)
            graph = espdl_quantize_onnx(
                onnx_import_file=str(quantization_onnx), espdl_export_file=str(model_path),
                calib_dataloader=loader, calib_steps=args.calibration_steps,
                input_shape=[1, 3, 224, 224], inputs=[golden_input], target="esp32s3", num_of_bits=8,
                collate_fn=lambda batch: batch.to("cpu"), setting=settings, device="cpu",
                error_report=False, export_test_values=True, test_output_names=list(OUTPUT_NAMES), verbose=0)
            export_ppq_graph(graph, TargetPlatform.NATIVE, graph_save_to=str(native_path))
            manifest["artifacts"] = {"espdl": artifact(model_path), "native_graph": artifact(native_path),
                                     "onnx": artifact(onnx_path), "quantization_onnx": artifact(quantization_onnx),
                                     "checkpoint": artifact(local_checkpoint)}
            manifest["golden_vectors"] = {"source_image": str(selected[0].image),
                                           "source_sha256": selected[0].image_hash,
                                           "input_rgb_sha256": hashlib.sha256(
                                               np.rint(golden_input.numpy()[0].transpose(1, 2, 0) * 255).astype(np.uint8).tobytes()).hexdigest(),
                                           "outputs": list(OUTPUT_NAMES)}
            if model_path.stat().st_size > args.max_model_bytes:
                raise ValueError(f"Candidate {model_path.stat().st_size} bytes exceeds budget {args.max_model_bytes}")
            # Verify the persisted supported native graph before relying on it.
            original_executor = TorchExecutor(graph, device="cpu")
            saved = load_native_graph(str(native_path))
            active_graph = saved
            executor = TorchExecutor(saved, device="cpu")
            with torch.no_grad():
                expected = original_executor.forward(golden_input, output_names=list(OUTPUT_NAMES))
                actual = executor.forward(golden_input, output_names=list(OUTPUT_NAMES))
            if not all(torch.equal(left, right) for left, right in zip(expected, actual, strict=True)):
                raise RuntimeError("Native graph save/reload changed the quantized golden output")
            manifest["native_graph_reload_check"] = "exact six-output match on calibration golden input"
            del original_executor, graph, saved
        else:
            native_path = args.native_graph.resolve()
            resolved_artifacts = {}
            for name in ("native_graph", "onnx", "espdl"):
                path = native_path if name == "native_graph" else native_path.parent / Path(prior["artifacts"][name]["path"]).name
                if sha256_file(path) != prior["artifacts"][name]["sha256"]:
                    raise ValueError(f"Saved candidate provenance does not match {name}: {path}")
                resolved_artifacts[name] = artifact(path)
            if prior["dataset"]["validation_manifest_sha256"] != manifest["dataset"]["validation_manifest_sha256"]:
                raise ValueError("Validation content/labels changed since this candidate was exported")
            onnx_path = native_path.parent / Path(prior["artifacts"]["onnx"]["path"]).name
            model_path = native_path.parent / Path(prior["artifacts"]["espdl"]["path"]).name
            manifest["source_export_manifest"] = artifact(native_path.parent / "quantization_manifest.json")
            manifest["artifacts"] = {**prior["artifacts"], **resolved_artifacts}
            manifest["parameter_count"] = prior["parameter_count"]
            active_graph = load_native_graph(str(native_path))
            executor = TorchExecutor(active_graph, device="cpu")

        if manifest["parameter_count"] > args.max_parameters or model_path.stat().st_size > args.max_model_bytes:
            raise ValueError("Candidate exceeds the requested parameter or ESP-DL file-size budget")
        quantized_score_thresholds = {}
        for name in ("score0", "score1", "score2"):
            variable = active_graph.variables[name]
            operation = variable.source_op
            config = operation.config.output_quantization_config[operation.outputs.index(variable)]
            if config.scale.numel() != 1 or config.offset.numel() != 1 or float(config.offset.item()) != 0.0:
                raise ValueError(f"Expected symmetric per-tensor int8 output quantization: {name}")
            quantized_score_thresholds[name] = espdl_score_threshold(float(config.scale.item()))
        manifest["settings"]["quantized_score_thresholds"] = quantized_score_thresholds

        if args.skip_evaluation:
            manifest["status"] = "exported; CPU evaluation pending"
            write_json(manifest_path, manifest)
            print(f"Candidate exported: {manifest['artifacts']['espdl']['path']}", flush=True)
            return
        manifest["status"] = "evaluating"
        write_json(manifest_path, manifest)
        options = ort.SessionOptions()
        options.intra_op_num_threads, options.inter_op_num_threads = args.threads, 1
        float_session = ort.InferenceSession(str(onnx_path), sess_options=options, providers=["CPUExecutionProvider"])
        if set(output.name for output in float_session.get_outputs()) != set(OUTPUT_NAMES):
            raise ValueError("Float reference does not have the six expected ESPDet output names")
        rows, stats = [], {"float_onnx": {"tp": [], "confidence": []}, "int8_simulation": {"tp": [], "confidence": []}}
        total_truth_boxes, quantized_seconds = 0, 0.0
        for index, sample in enumerate(validation):
            tensor, mapping = prepare_image(sample.image, args.capture_max_side)
            float_outputs = dict(zip(OUTPUT_NAMES, float_session.run(list(OUTPUT_NAMES), {float_session.get_inputs()[0].name: tensor}), strict=True))
            begin = time.perf_counter()
            with torch.no_grad():
                raw = executor.forward(torch.from_numpy(tensor), output_names=list(OUTPUT_NAMES))
            quantized_seconds += time.perf_counter() - begin
            quantized_outputs = {name: value.detach().cpu().numpy() for name, value in zip(OUTPUT_NAMES, raw, strict=True)}
            row = {"image": str(sample.image), "image_sha256": sample.image_hash, "label_sha256": sample.label_hash,
                   "has_deer": sample.positive, "width": mapping["width"], "height": mapping["height"],
                   "source_width": mapping["source_width"], "source_height": mapping["source_height"]}
            for name, outputs in (("float_onnx", float_outputs), ("int8_simulation", quantized_outputs)):
                predictions = decode_espdet(outputs, mapping,
                                            quantized_score_thresholds=quantized_score_thresholds if name == "int8_simulation" else None)
                row[name] = {"score": float(predictions[:, 4].max()) if len(predictions) else 0.0,
                             "detections_xyxy_score": predictions.tolist()}
                if not args.skip_box_metrics:
                    stats[name]["tp"].append(match_detections(predictions, sample.boxes, mapping))
                    stats[name]["confidence"].append(predictions[:, 4])
            row["quantization_score_delta"] = row["int8_simulation"]["score"] - row["float_onnx"]["score"]
            total_truth_boxes += len(sample.boxes)
            rows.append(row)
            if (index + 1) % 50 == 0 or index + 1 == len(validation):
                print(f"Evaluated {index + 1}/{len(validation)} held-out images", flush=True)

        report = {"schema_version": 1, "scope": manifest["scope"], "artifacts": manifest["artifacts"],
                  "runtime_packages": runtime_packages,
                  "dataset": manifest["dataset"], "settings": manifest["settings"], "parameter_count": manifest["parameter_count"],
                  "image_count": len(rows), "deer_images": sum(row["has_deer"] for row in rows),
                  "quantized_host_execution_ms_per_image": quantized_seconds * 1000 / len(rows),
                  "temporal_gate": "Not evaluated: these are unordered still images", "images": rows}
        for name in stats:
            presence_rows = [{"image": row["image"], "has_deer": row["has_deer"], "score": row[name]["score"]} for row in rows]
            report[name] = {"image_presence": summarize_presence(presence_rows, list(args.thresholds))}
            if not args.skip_box_metrics:
                from ultralytics.utils.metrics import ap_per_class
                confidence = np.concatenate(stats[name]["confidence"])
                correct = np.concatenate(stats[name]["tp"])
                if total_truth_boxes:
                    metric = ap_per_class(correct, confidence, np.zeros(len(confidence)), np.zeros(total_truth_boxes), plot=False)
                    report[name]["detector"] = {"map50": float(metric[5][:, 0].mean()),
                                                 "map50_95": float(metric[5].mean()),
                                                 "scope": "One-class AP, IoU-greedy matching, ESP-DL NMS floor .10/top10; not directly comparable to Ultralytics floor .001/top300"}
                else:
                    report[name]["detector"] = {"map50": None, "map50_95": None, "scope": "No positive ground-truth boxes"}
        deltas = np.asarray([row["quantization_score_delta"] for row in rows])
        report["quantization_score_difference"] = {"mean_absolute": float(np.abs(deltas).mean()),
                                                     "maximum_absolute": float(np.abs(deltas).max())}
        report_path = output_dir / "quantized_evaluation.json"
        write_json(report_path, report)
        manifest["status"] = "exported and evaluated with ESP-PPQ CPU simulation; board validation pending"
        manifest["evaluation"] = artifact(report_path)
        write_json(manifest_path, manifest)
        print(json.dumps({name: report[name] for name in ("float_onnx", "int8_simulation", "quantization_score_difference")}, indent=2))
        print(f"CPU quantization evaluation written to {report_path}", flush=True)
    except Exception as error:
        manifest["status"], manifest["error"] = "failed", f"{type(error).__name__}: {error}"
        write_json(manifest_path, manifest)
        raise


if __name__ == "__main__":
    main()
