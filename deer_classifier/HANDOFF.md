# Deer classifier handoff

## Continuation on Windows — October 29, 2026

The user confirmed **Adafruit ESP32-S3 TFT Feather** and the **Adafruit OV5640
parallel camera breakout**, linking the manufacturer guides. No board is
connected to this computer. Immediate acceptance is a printed-deer camera
smoke test with serial output; sound/light deterrence and photo capture remain
later milestones.

Only `artifacts/deer.espdl` survived in this checkout. The original Mac's
dataset, `.pt` checkpoints and temporary Python/ESP-Detection environments are
absent here. **No new training, held-out model evaluation or physical test has
been performed on Windows.** Do not interpret the new host software tests as
model accuracy or hardware success. The historical results below still apply.

Implemented continuation:

- `firmware/smoke_test/`: standalone ESP-IDF app, pinned ESP-DL 3.3.14 and
  esp32-camera 2.1.3, QVGA JPEG → RGB888 → centered 224² letterbox114 → int8
  ESPDet. Weights remain in flash. USB serial prints BOOT/hash, gate/inference
  checks, READY, FRAME scores/timing/PSRAM and DEER_DETECTED/DEER_CLEARED.
- `sdkconfig.feather_ov5640.defaults`: proposed wiring for the confirmed boards.
  Follow the firmware README and check actual wires; the normal configuration
  leaves camera pins unconfirmed and intentionally stops before capture.
- `smoke_check.py`: continuous serial recorder and guided blank/deer/blank
  protocol, with replayable JSONL evidence and strict failure handling.
- `evaluate_checkpoint.py` and `image_metrics.py`: one held-out validation pass
  reports detector mAP and image-level confusion at multiple thresholds,
  including 0.85. Rejects NMS truncation, dropped samples, stale/missing labels,
  invalid scores and non-deer checkpoints. Requires restored `.pt`/dataset.
- Training/export now default to automatic device selection, preserve unique
  run directories and provenance, protect existing output models, and stage
  quantization before publishing. Use `artifacts/deer_candidate.espdl` for a
  new candidate. The old warning below about automatic run overwrites is
  historical; it no longer describes the current scripts.
- Fixed `prepare_dataset.py` resolving a relative archive after changing cwd.
  Added focused host tests for metrics, export safety, preparation and smoke
  evidence. Run `python -m unittest discover -s tests -v` from this folder.

The retained artifact remains exactly 499,712 bytes, SHA-256
`f4baa40014b3b5476e05e5007ab6e83a1a19bdc680c12dba86761841e02fc450`.
Read-only parsing using the downloaded ESP-DL schema verified one INT8 NHWC
input `[1,224,224,3]` and INT8 score/box outputs at 28², 14², 7² with one deer
channel and four box channels. It has **no embedded golden input/output
vectors**, so `Model::test()` cannot establish numerical equivalence.
Firmware's synthetic-frame inference check only verifies successful execution
and finite scores; it does not verify recognition.

ESP-IDF 5.4.2 and its compiler are installed locally in ignored `.tools/`.
`firmware/smoke_test/idf-local.ps1` runs that installation. Bundled host Python:
`C:/Users/ayanl/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.
It lacks torch/Ultralytics; the separate local IDF Python environment contains
pyserial. Build records live in `.tools/smoke-build.log` and
`.tools/smoke-configured-build.log`. A configured compile-only build uses an
ignored sdkconfig under `.tools/`, separate from the unconfirmed normal config.
No device was flashed. Both the normal unconfigured build and the full camera
and model configured build passed with ESP-IDF 5.4.2. The configured binary is
1,853,456 bytes (about 1.77 MiB), leaving 55% of the application partition free.
This measures flash usage, not runtime PSRAM headroom. All 25 host unit tests
pass. The configured build embeds the unchanged model; startup hardware and
recognition checks have not run.

Next: wire and connect the physical unit,
configure/flash, run `smoke_check.py --port COMx`, and use observed scores to
decide whether the experimental candidate can pass the print check. Restore
training data/checkpoints for quantitative improvements. Do not claim the
physical milestone passed until there is a real passing serial evidence log.

## Historical Mac handoff

This document captures the current implementation and the work needed to continue it. The next model should read this file and `README.md`, inspect the source files listed below, then continue improving and validating the model. **Do not treat the current checkpoint as product-ready:** its validation results are weak and the real camera view has not been tested.

## User goal and hardware

- Detect a deer in a reasonably broad camera view and produce a stable deer / no-deer signal for the rest of the firmware.
- Run all image inference on the device; cloud or server inference is out of scope because of latency.
- Target hardware: Adafruit ESP32-S3 TFT Feather, OV5640 camera, 3.7 V battery. The Feather has 4 MB flash and 2 MB PSRAM. The OV5640 sensor is 5 MP capable; use the intended 2 MP mode only if its camera path fits the memory budget. VGA capture followed by resize or letterbox is the current safe starting point.
- The user asked for a lightweight, accurate model and confirmation over multiple frames. There is no field-view specification, acceptable false-positive rate, maximum latency, or battery-current budget yet.

## Current implementation

The code uses Espressif ESP-Detection's ESPDet-Pico **one-class object detector** (class 0 = deer), not a whole-frame binary classifier. Detection is a better fit for a wide view because a deer can occupy only part of a frame. Input is 224 × 224 RGB, int8 ESP-DL export target is `esp32s3`, and the firmware helper feeds the maximum deer-box score into a 2-of-3 temporal gate at confidence 0.85. Camera/inference failure clears the gate.

The temporal gate and export path exist, but `firmware/deer_presence.hpp` is a thin adapter to Espressif's generated `ESPDetDetect` component. It has **not** been compiled inside the lab's ESP-IDF firmware, tested on the Feather, or measured for latency/current. `artifacts/deer.espdl` is the current experimental export.

## Current training and results

The available dataset is prepared locally at `deer_classifier/datasets/deer` (about 5.4 GB; ignored by Git): 2,581 deer images with boxes from the public Kaggle deer camera-trap dataset plus 750 empty-label hard negatives from Idaho Camera Traps metadata (600 train, 150 validation). Camera locations are held out between splits. Effective split size: 2,729 train and 602 validation images. Public camera-trap scenes do not represent the actual feeder view, and the validation set is too small to establish product reliability.

The active session was `13987`; it has now exited successfully and wrote the ESP-DL export. The refined run used MPS, 20 maximum epochs, batch 16, AdamW, LR 0.0005, 0.5 warmup epochs, and patience 8. It started from the previous deer checkpoint at `artifacts/deer_espdet_pico/weights/best.pt` (that checkpoint had initially been fine-tuned from Espressif's cat example), then early-stopped after epoch 9. The 488 KiB `artifacts/deer.espdl` was emitted from the trainer's selected `best.pt`.

Recorded validation results from `artifacts/deer_espdet_pico/results.csv`:

| Epoch | Precision | Recall | mAP50 | mAP50–95 |
|---:|---:|---:|---:|---:|
| 1 | 0.484 | 0.285 | 0.303 | **0.126** |
| 2 | 0.518 | 0.267 | 0.274 | 0.109 |
| 3 | 0.433 | 0.294 | 0.259 | 0.093 |
| 4 | 0.438 | 0.317 | 0.296 | 0.103 |
| 5 | 0.408 | 0.309 | 0.271 | 0.094 |
| 6 | 0.458 | 0.282 | 0.270 | 0.088 |
| 7 | 0.390 | 0.300 | 0.265 | 0.090 |
| 8 | 0.421 | 0.272 | 0.259 | 0.087 |
| 9 | 0.444 | 0.296 | 0.286 | 0.089 |

Epoch 1 is the trainer's best checkpoint by mAP50–95, but these numbers are not strong enough to claim an accurate detector. A time-limit warning occurred in epoch 9 validation; verify the evaluation budget and recompute clean held-out metrics before comparing runs. The compatibility patch raises the Ultralytics NMS budget to 0.5 seconds per image, but one difficult validation batch still exceeded its 15-second budget. The later validation metrics may therefore omit detections. The early best epoch did not show that warning in the training log.

The upstream ESP-Detection example reports about 126 ms/image for ESPDet-Pico on ESP32-S3; this is only an upstream reference. No timing or battery measurement has been made on this board/camera combination.

## Files in this folder

- `README.md` — setup, dataset preparation, design notes, and deployment steps.
- `train_embedded.py` — public training CLI and dataset/layout checks.
- `run_espdet_training.py` — invokes ESP-Detection training, export, and int8 quantization.
- `espdet_compat.py` — bridges upstream checkpoint/export API changes and patches NMS/quantizer settings.
- `evaluate_checkpoint.py` — held-out detector mAP evaluation; currently does not report image-level deer/no-deer metrics at the gate threshold.
- `export_embedded.py` — re-export an existing trained checkpoint as ESP-DL int8.
- `prepare_dataset.py` — converts the Kaggle deer archive to YOLO format and makes a camera-location split.
- `fetch_negatives.py` — samples public Idaho hard negatives and writes empty YOLO labels.
- `rebalance_splits.py` — keeps image/label pairs from the same camera location in one split.
- `temporal_gate.py` / `temporal_gate.hpp` — Python and allocation-free C++ 2-of-3 temporal gate implementations.
- `firmware/deer_presence.hpp` — ESP-DL-to-gate adapter; requires Espressif's generated `ESPDetDetect` model component.
- `requirements-espdetection.txt` — tested Python package versions.
- `artifacts/deer.espdl` — current 488 KiB experimental ESP32-S3 model (the only generated artifact intentionally included by `.gitignore`).
- `artifacts/deer.info`, `artifacts/deer.json`, training checkpoints, and datasets are local/ignored outputs. `best.pt` and `last.pt` exist on the current machine but are not committed.

## Local environment and reproduction

At handoff time the current machine has:

- Python environment: `/private/tmp/espdet311` (Python 3.11; temporary and may be removed).
- ESP-Detection checkout: `/private/tmp/esp-detection`, commit `28de5902a357d99dd9a5db0f52905255641c5a78`.
- Training log: `/private/tmp/deer-train-refined.log`.
- Prepared dataset: `deer_classifier/datasets/deer`.

From `deer_classifier/`, after restoring those dependencies/data if needed:

```bash
/private/tmp/espdet311/bin/python train_embedded.py \
  --esp-detection /private/tmp/esp-detection \
  --python /private/tmp/espdet311/bin/python \
  --dataset datasets/deer \
  --pretrained artifacts/deer_espdet_pico/weights/best.pt \
  --device mps --epochs 30 --batch-size 16 \
  --optimizer AdamW --learning-rate 0.0005 --warmup-epochs 0.5 \
  --output artifacts/deer.espdl
```

For a fresh run, use the upstream `examples/cat_detection/espdet_pico_224_224_cat.pt` checkpoint instead of the current deer `best.pt`. The cat model is only a transfer-learning initialization, not a deer detector. Repeated training overwrites the named `artifacts/deer_espdet_pico` run directory; copy the checkpoint/log first if it needs to be preserved.

## Recommended next work

1. Inspect the dataset samples, labels, image sizes, and camera-location split. Confirm negatives really contain no deer and look for annotation/source distribution problems.
2. Recompute clean held-out evaluation for `best.pt`. Fix the NMS time-budget warning (for example, test a smaller validation batch and a higher per-image NMS budget), and log exact evaluator settings.
3. Add image-level deer/no-deer metrics at confidence thresholds, including the deployed 0.85 threshold, and evaluate the 2-of-3 gate on ordered held-out frame sequences if sequence metadata can be retained. Report false-positive and missed-deer rates, not just bounding-box mAP.
4. Improve training/transfer learning and compare candidate checkpoints on the same clean split. Do not blindly accept epoch 1 or the current 488 KiB export. Consider whether the training data or initial weights are the main limitation before increasing model size.
5. Keep the input field of view broad and check distant/small deer performance. Tune 224 vs larger input against actual ESP32-S3 latency and memory once hardware is available.
6. Integrate into the Feather's ESP-IDF project, feed OV5640 frames through the exact preprocessing expected by ESPDet-Pico, compile/flash, then measure camera-to-signal latency and average LiPo current.
7. Tune the confidence threshold and temporal gate against the product's acceptable false-alarm/missed-deer tradeoff. Current 0.85 and 2-of-3 are unvalidated starting values.

## Suggested prompt for the next model

> Continue the deer classifier work from `deer_classifier/HANDOFF.md`. Inspect the existing code, dataset preparation, artifacts, and training results before changing anything. The current quantized model is only an experimental baseline: held-out detector mAP50–95 is 0.126 at best, the dataset is public camera-trap data, and the epoch-9 validation hit an NMS time limit. Improve the model and its evaluation, preserve reproducibility, and clearly separate measured facts from hardware assumptions. Produce the strongest defensible ESP32-S3 ESP-DL artifact you can, with clean held-out image-level and detector metrics. Do not claim field readiness without testing the real camera view, firmware integration, latency, and battery current.
