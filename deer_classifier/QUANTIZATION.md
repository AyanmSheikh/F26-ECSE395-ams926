# Reproducible int8 candidate evaluation

`quantize_and_evaluate.py` exports a trained one-class deer checkpoint for
ESP32-S3 and checks the quantized graph using ESP-PPQ's supported CPU
`TorchExecutor`. It preserves the deployed `artifacts/deer.espdl`; every run
requires a new output directory and writes `deer_candidate.espdl` there.

From the repository root, using the Python 3.11 environment with the pinned
training/export dependencies:

```powershell
.tools/espdet311/Scripts/python.exe deer_classifier/quantize_and_evaluate.py `
  --esp-detection .tools/esp-detection `
  --checkpoint deer_classifier/artifacts/candidate_run/weights/best.pt `
  --dataset deer_classifier/datasets/deer `
  --output-dir deer_classifier/artifacts/candidate_run/int8 `
  --threads 2
```

Substitute the actual candidate checkpoint and a new destination directory.
The checkpoint must identify class 0 as deer. Defaults retain the 224 × 224
ESPDet-Pico architecture, require at most 400,000 parameters, and cap the
complete ESP-DL file at 750 KiB (768,000 bytes), including golden tensors.
This file-size check does not establish real-board latency or peak RAM use.

The script audits explicit label files and rejects identical image contents
across training and validation. Calibration uses only training images: 32
steps of eight images, half deer and half confirmed negatives, sampled with
seed 395. Equalization uses four iterations. Validation images are never used
to set quantization ranges or generate golden tensors.

By default, host images first receive an aspect-preserving Pillow BILINEAR
downsample with maximum side 320, leaving smaller images untouched. This is
a **QVGA acquisition proxy**, approximating the fact that the OV5640 supplies
an already downsampled frame before inference. It is not the exact sensor
binning, ISP, or JPEG pipeline. Use `--capture-max-side 0` for the earlier raw
original-resolution path. The selected setting is recorded in the manifest.

After that optional acquisition step, both calibration and evaluation use
RGB divided by 255, the camera runtime's
centered letterbox with padding 114, and ESP-DL's float32 geometry and
`floor(destination_index * inverse_scale)` nearest-neighbor sampling. This
differs from stretching an image to a square and from the usual center-based
nearest-neighbor resize. The same host preprocessing is applied to both the
float ONNX reference and the quantized CPU graph for a fair comparison.

Each run creates:

- `deer_candidate.espdl`: S3 int8 deployment candidate with a training-derived
  golden input and six expected output tensors for future `Model::test()`.
- `deer_candidate.native`: official PPQ native graph containing quantization
  state for repeated host evaluation without recalibration.
- `source.pt` and `source.onnx`: exact source checkpoint and preserved float
  reference used in the comparison. `quantization_input.onnx` is a separate
  working copy for the quantizer's ONNX resimplification.
- `quantization_manifest.json`: source/model/native hashes, package versions,
  parameter count, dataset fingerprints, calibration selections, settings,
  source-code hashes, and an exact native save/reload output check.
- `quantized_evaluation.json`: paired float/quantized per-image detections,
  confidence scores, threshold confusion counts, detector AP, and score drift.

Presence thresholds default to 0.10, 0.25, 0.50, 0.70, 0.85, and 0.95. Box
decoding follows the firmware's three ESPDet strides, integer source-image
coordinates, inclusive NMS at IoU 0.70, score floor 0.10, and at most ten boxes.
For int8, the firmware first quantizes the inverse-sigmoid cutoff using each
score head's scale. The evaluator reproduces that cutoff and records each
head's effective probability floor; it can differ slightly from nominal 0.10.
The host reports one-class AP at IoU 0.50:0.05:0.95 with greedy IoU matching.
Its floor/top-ten setting makes those AP numbers distinct from the standard
Ultralytics evaluation at floor 0.001 with 300 detections. Compare candidates
under the same evaluator settings. Unordered validation stills cannot measure
the two-of-three temporal gate.

Use `--skip-evaluation` to export now and evaluate the saved graph later:

```powershell
.tools/espdet311/Scripts/python.exe deer_classifier/quantize_and_evaluate.py `
  --native-graph deer_classifier/artifacts/candidate_run/int8/deer_candidate.native `
  --dataset deer_classifier/datasets/deer `
  --output-dir deer_classifier/artifacts/candidate_run/int8_recheck `
  --threads 2
```

The evaluator verifies the `.native`, ONNX, and ESP-DL hashes against the
export manifest, and requires unchanged validation contents and labels.
It automatically uses the capture preprocessing stored for that graph;
exports from before the capture-proxy option are treated as legacy raw input.
An incompatible `--capture-max-side` override is rejected. Changing capture
preprocessing requires a new export and new training-only calibration.
Failed or incomplete runs remain marked failed instead of publishing partial
metrics. `--skip-box-metrics` omits AP computation while retaining presence
metrics and paired per-image predictions.

For a controlled raw-versus-proxy comparison, a new checkpoint export can
use `--onnx-reference <prior-run/source.onnx>`. Its hash and association with
the identical checkpoint are verified against the prior export manifest.
The unchanged float ONNX file is then used for reference inference, while
calibration and validation use the new capture setting. Holding that float
model and postprocessor fixed isolates the effect of host preprocessing.
Differences from a separate Ultralytics validation also include NMS, score
floor, detection limits, and metric conventions, so they cannot by themselves
be attributed to nearest-neighbor sampling.

The CPU result measures **ESP-PPQ quantization simulation**, not execution of
the `.espdl` binary or a physical board. The associated export may still need
runtime compatibility checks. The installed QEMU failed a known numerical
oracle and must not supply classifier accuracy metrics. After choosing a
candidate, run its embedded golden vectors on the real ESP32-S3, then perform
the blank → printed deer → blank camera smoke test before integrating any
deterrence or photo-capture logic.
