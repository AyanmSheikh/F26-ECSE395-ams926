# Embedded deer detection for the ESP32-S3

For continuation context, file inventory, current training results, and next steps, see [HANDOFF.md](HANDOFF.md).

## First milestone: printed-deer camera smoke test

Use the standalone [ESP-IDF camera test](firmware/smoke_test/README.md) for the
confirmed Adafruit ESP32-S3 TFT Feather and Adafruit OV5640 breakout. It embeds
the existing 499,712-byte int8 model, captures QVGA JPEG, converts to RGB, runs
224 × 224 inference locally, and prints `DEER_DETECTED` after two confident
frames in a three-frame window. Removing the print produces `DEER_CLEARED`.
Per-frame scores, timings, memory and failures appear on USB serial. The guide
includes a proposed complete wiring map and an opt-in configuration profile.

No device is connected to this Windows computer, so the physical test remains
pending. The retained model is experimental; no new training or accuracy
measurement has been performed here. This checkout has no `.pt` checkpoints
or training images from the previous Mac. Restore them to improve the existing
model, or rebuild the dataset and fine-tune a fresh upstream checkpoint.

After wiring, configuring and flashing the test, close other serial monitors
and run from this folder with Python and pyserial installed:

```powershell
python -m pip install -r requirements-smoke.txt
python smoke_check.py --port COM5
```

The recorder guides an empty-background → printed-deer → empty-background test,
discards three settling frames per phase, measures ten frames per phase, and
saves all serial evidence to `artifacts/smoke/`. It reads continuously while
you change the scene, so errors and resets are retained. A pass requires no
confirmed deer on either empty phase and at least two confirmed frames with
the deer print. It fails on missing frames, invalid scores, gate inconsistency,
errors, resets or incomplete phases. Repeat with different deer and non-deer
prints before proceeding to deterrence and photo-capture integration.

Host checks use no ML dependencies:

```powershell
python -m unittest discover -s tests -v
```

The target is the Adafruit ESP32-S3 TFT Feather (4 MB flash, 2 MB PSRAM) with the Adafruit OV5640 camera, powered from a 3.7 V LiPo. The embedded path in this folder uses Espressif's ESPDet-Pico detector and ESP-DL export, then turns repeated deer detections into a stable deer-present signal. Detecting a deer region in the frame is more suitable for the requested broad view than classifying the whole frame: birds and background can remain in view without turning the whole image into one scene label.

The upstream ESPDet-Pico cat example reports 0.36 M parameters at 224 × 224 and 126.2 ms on an ESP32-S3. That is an upstream benchmark, not a measurement on this camera/board/battery setup. It is a useful starting point for testing. Adafruit's OV5640 breakout has a 5 MP sensor. For this 2 MB PSRAM board, begin with VGA (640 × 480) capture and resize/letterbox into the model input; only use 2 MP capture if the camera can deliver JPEG or stream-resize it without allocating a full-resolution RGB frame. Benchmark the complete camera-to-result path and average battery current on the actual hardware.

## Public data and preparation

The initial candidate is the public [deer camera-trap dataset](https://www.kaggle.com/datasets/winnerbishal/deer-cameratraps), containing annotated deer boxes from Idaho camera-trap images. It is based on the [Idaho Camera Traps dataset](https://lila.science/datasets/idaho-camera-traps/). The original Idaho annotations are sequence-level, not per-image, and the Kaggle dataset's deer boxes were manually annotated; keep related bursts/sequences together when creating train/validation splits. Attribute Idaho Department of Fish and Game when reporting or publishing results, and check the source dataset terms before redistributing images.

Download the public Kaggle dataset with the Kaggle CLI (account/API access may be required):

```bash
kaggle datasets download -d winnerbishal/deer-cameratraps -p datasets/source
python prepare_dataset.py datasets/source/deer-cameratraps.zip
```

The archive currently contains 2,581 deer images with box labels (the publisher's split is 2,064/517). `prepare_dataset.py` regroups images by camera location into a roughly 80/20 training/validation split and converts them to the expected YOLO format:

```text
datasets/deer/
  images/train/       # deer and hard-negative scenes
  images/val/         # distinct cameras/sequences from training
  labels/train/       # YOLO .txt files; one class, 0 = deer
  labels/val/
```

The deer archive has no empty-scene negatives. Download the official [Idaho Camera Traps metadata](https://storage.googleapis.com/public-datasets-lila/idaho-camera-traps/idaho-camera-traps.json.zip) (25.5 MB), then add a balanced set of empty, bird, squirrel, fox, coyote, elk, and other non-target scenes. The sampler chooses one image per sequence, holds whole camera locations out of validation, and writes empty YOLO labels:

```bash
python fetch_negatives.py /path/to/idaho-camera-traps.json.zip \
  --dataset datasets/deer --train-count 600 --validation-count 150
python rebalance_splits.py datasets/deer
```

The sampler downloads only the selected images rather than the full 1.5-million-image archive. Its category labels are sequence-level and the source contains no human/vehicle images; this is suitable for hard negatives but is still not a substitute for scenes from the actual feeder view. Confirm no images from a camera location occur in both splits before training.

The prepared training run used 2,581 annotated deer images and 750 empty-label non-deer images (600 train, 150 validation), for 2,729 training and 602 validation frames after location-level splitting. The downloaded images and generated checkpoints are excluded from Git; the trained `.espdl` artifact is retained separately.

## Train and export an ESP32-S3 model

The exporter uses Espressif's maintained [ESP-Detection](https://github.com/espressif/esp-detection) training, export, and quantization code to produce an ESP-DL `.espdl` model. ESP-Detection's broad Ultralytics lower bound can select releases that do not match its custom `ESPDetect` head. The runner pins the tested Ultralytics version and transfers only compatible checkpoint tensors. The quantizer also needs newer ONNX packages than the upstream requirements specify, so use Python 3.11+ with these [compatible requirements](requirements-espdetection.txt). For example:

```bash
conda create -n espdet python=3.11
conda activate espdet
python -m pip install -r deer_classifier/requirements-espdetection.txt
git clone https://github.com/espressif/esp-detection.git
```

ESP-IDF 5.3 or newer is required to integrate the `.espdl` model with ESP-DL and flash the board firmware.

The upstream example checkpoint below is a small cat detector used as a transfer-learning starting point; it is not a deer model. Fine-tune it with the prepared deer and negative examples before using it. Get the checkpoint from [Espressif's ESP-Detection example](https://github.com/espressif/esp-detection/blob/main/examples/cat_detection/espdet_pico_224_224_cat.pt), and clone Espressif's repo. From this folder, run:

```bash
python train_embedded.py \
  --esp-detection ../esp-detection \
  --python "$(which python)" \
  --dataset datasets/deer \
  --pretrained ../esp-detection/examples/cat_detection/espdet_pico_224_224_cat.pt \
  --device auto \
  --output artifacts/deer_candidate.espdl
```

The wrapper caps the run at 30 epochs with early stopping rather than using the upstream entry point's 1,200-epoch default. It uses AdamW at 0.0005 with a half-epoch warmup; override with `--optimizer`, `--learning-rate`, and `--warmup-epochs`. The default `--device auto` chooses CUDA, MPS or CPU on the training interpreter. Each run has a new directory; `--run-name` names it explicitly and refuses reuse. `--patience`, `--workers` (default 0 for Windows) and `--seed` are exposed. Train at 224 × 224 first; the smoke firmware validates that exact input contract.

An existing output model is protected unless `--overwrite-output` is supplied.
Training and quantization stage their results within the run directory before
publishing a successful export. `deer_run.json` records source/checkpoint
hashes, dependency versions, upstream revision, settings and export hash.
Evaluate a candidate before deliberately replacing `artifacts/deer.espdl`.
The per-frame score is a maximum box confidence, not a calibrated probability.

To re-export a saved checkpoint without retraining, use `export_embedded.py` with its `best.pt` and the training images for int8 calibration. The deployable output is `artifacts/deer.espdl`.

To obtain clean held-out metrics after restoring checkpoints and data:

```powershell
python evaluate_checkpoint.py --esp-detection ../esp-detection --checkpoint artifacts/YOUR_RUN/weights/best.pt --data artifacts/YOUR_RUN_dataset.yaml --device cpu --batch-size 1 --output artifacts/candidate_evaluation.json
```

The evaluator reports box mAP and image-level precision, recall, false-positive
rate and missed-deer rate at 0.25, 0.50, 0.70, 0.85 and 0.95. It saves per-image
scores and evaluator settings and rejects truncated NMS, missing/stale labels
and excluded samples. These are float-checkpoint results; they do not validate
the quantized artifact or temporal behavior on real ordered camera frames.

## Multi-frame trigger

[`temporal_gate.hpp`](temporal_gate.hpp) is the firmware-side, allocation-free 2-of-3 frame gate with an 0.85 deer-confidence threshold. Pass the maximum class-0 deer-box score from each frame (or zero when no deer box is present); an invalid camera/inference frame clears history so stale positives cannot trigger the response. `temporal_gate.py` provides the same policy for host-side integration. Keep the response off for uncertain or failed results. The 2-of-3 and 0.85 values are starting defaults to tune against the false-alarm/missed-deer tradeoff, not validated product limits.

[`firmware/smoke_test`](firmware/smoke_test/README.md) supplies the standalone
OV5640 camera path and loads the raw retained model directly. The older
[`firmware/deer_presence.hpp`](firmware/deer_presence.hpp) is a separate adapter
requiring Espressif's generated `ESPDetDetect` component; it is not used by the
standalone test. Both use the shared temporal gate. Camera/inference failures
and invalid C++ scores clear history.

## Remaining measurements

- Confirm the exact OV5640 breakout/lens and camera driver output format (JPEG or RGB), then use matching decode, crop/letterbox, and color conversion in firmware.
- Measure how much of the input frame the feeder/approach region occupies. Train and validate with the same field of view; do not crop the model input to a tiny region.
- Measure model plus camera latency and average battery current at the intended capture interval. The detector benchmark is about 126 ms per image on ESP32-S3; taking fewer frames and sleeping between PIR-triggered checks will save energy.
- Tune the confidence threshold and 2-of-3 window on held-out scenes. Night/IR, glare, rain, blur, partial deer, birds, and empty-feeder frames need particular attention.
