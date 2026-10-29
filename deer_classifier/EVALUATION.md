# Restored checkpoint evaluation — October 29, 2026

The restored `best.pt` misses **all 517 deer images at the deployed 0.85
confidence threshold**. Its image-level accuracy at that threshold is 14.12%
(85 correct negatives out of 602), with 0% deer recall. This operating point
is unusable on the held-out dataset. No training or threshold change was made
during this evaluation.

## Dataset and provenance

The original Mac validation set was restored from the user's three Google
Drive ZIPs under `C:/Stuff/`, read without modification. It contains 602 JPEG
images, 517 with deer and 85 explicit empty-label negatives, and 703 deer boxes.
ZIP-directory auditing covered 2,729 canonical training image names: the 101
training camera locations and 29 validation locations are disjoint, with no
shared image filenames. Sixty-five byte-identical numbered Drive copies were
preserved outside the evaluation folders. Every validation image has one
matching, validated YOLO label. This public camera-trap data is not a physical
printed-deer or deployment-scene test.

Local evidence is retained in ignored files:

- `artifacts/original_mac_restore.json`: source ZIP metadata, restored-file
  SHA-256/CRC values, duplicate handling and camera split audit.
- `artifacts/pc_evaluation_best.json`: all 602 per-image scores, label hashes,
  confusion counts, detector metrics, settings and library versions.
- Checkpoint SHA-256:
  `57d0481689a1920af67cec3b67d3db58e8bd2a2c59392f0d10acbc1b336fd156`.
- Evaluation JSON SHA-256:
  `e68349e02d3d1570cf8085b6b0a3992c49792bade9711e9d4900f1df5505b8c4`.

## Measured best.pt results

Scores are the maximum class-0 deer-box confidence in each image; an image is
positive when its score is at least the threshold.

- **Threshold 0.85:** TP 0, FP 0, TN 85, FN 517; accuracy 14.12%, recall 0%,
  false-positive rate 0%, balanced accuracy 50.00%. Precision is undefined
  because there were no positive predictions.
- **Threshold 0.25:** TP 175, FP 14, TN 71, FN 342; accuracy 40.86%, recall
  33.85%, precision 92.59%, false-positive rate 16.47%, balanced accuracy 58.69%.
  Lowering the threshold alone still misses about two thirds of deer images.
- The highest score across all 602 images was 0.7252197862, below 0.85.
  Detector mAP50 was 0.307949 and mAP50–95 was 0.128958. Box mAP and
  image-level accuracy measure different behavior.

The set is strongly skewed toward deer: always predicting deer would give
85.88% raw accuracy and 50% balanced accuracy. Interpret accuracy with class
counts, recall and false-positive rate. Unordered still images do not evaluate
the 2-of-3 temporal gate.

## last.pt comparison

The same evaluation on `last.pt` also missed every deer at 0.85: TP 0, FP 0,
TN 85, FN 517; accuracy 14.12%, recall 0%. At 0.25 it produced TP 182, FP 9,
TN 76, FN 335: accuracy 42.86%, recall 35.20%, precision 95.29%, false-positive
rate 10.59%, balanced accuracy 62.31%. Its mAP50 was 0.290698 and mAP50–95
0.101031, below `best.pt`; its maximum image score was 0.6060715914.
Although its low-threshold image metrics improved slightly, both checkpoints
still miss most deer and neither is ready for the intended behavior.

Evidence: `artifacts/pc_evaluation_last.json`, SHA-256
`2b281513614922b36e470dd26a31a938da704a4ead797959e7ada6c31e5a0770`;
checkpoint SHA-256
`2adad980b48b0b415fbb7874e7cc62379fcc86129b77a470b0c8ab2a89a0b1ea`.
Saved figures: [confusion chart](artifacts/pc_evaluation_confusion.png) and
[validation examples](artifacts/pc_evaluation_examples.jpg). The model and
deployed threshold remain unchanged.

## Reproduction

Run from the repository root after restoring the local files:

```powershell
.\.tools\espdet311\Scripts\python.exe deer_classifier/evaluate_checkpoint.py `
  --esp-detection .tools/esp-detection `
  --checkpoint deer_classifier/artifacts/deer_espdet_pico/weights/best.pt `
  --data deer_classifier/artifacts/pc_eval_dataset.yaml `
  --device cpu --batch-size 1 `
  --output deer_classifier/artifacts/pc_evaluation_best.json
```

The isolated environment uses Python 3.11.9, torch 2.2.0+cpu, Ultralytics
8.4.191, and ESP-Detection revision
`28de5902a357d99dd9a5db0f52905255641c5a78`. Evaluation uses square 224 × 224
inputs, `rect=False`, prediction floor 0.001, NMS IoU 0.7, at most 300 detections,
and a five-second NMS budget per image. Missing/stale labels, omitted images,
invalid scores or NMS truncation fail evaluation.

## Embedded status

These results evaluate the float PyTorch checkpoint. The retained 499,712-byte
ESP-DL artifact is unchanged, SHA-256
`f4baa40014b3b5476e05e5007ab6e83a1a19bdc680c12dba86761841e02fc450`.
Its embedded numerical accuracy remains unvalidated. The experimental QEMU
path failed a CPU golden-value check (expected -102, observed 127); its
saturated 1.0 scores must not be used as accuracy measurements. Fix and pass
that numerical check before accepting emulator results.

The 37 passing host software tests verify supporting code, not recognition.
No ESP32 camera, printed-image, physical latency, PSRAM runtime-headroom or
battery-current measurement has passed. Improve and re-evaluate the model,
then pass the real serial smoke test before deterrence/photo integration.
