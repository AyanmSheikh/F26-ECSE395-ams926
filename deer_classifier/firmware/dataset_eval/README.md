# Evaluate the retained ESP32-S3 model on image files

**Experimental — blocked for accuracy evaluation.** The installed official
QEMU `esp_develop_9.2.2_20260417` failed a numerical oracle made from the
official ESPDet-Pico cat checkpoint with CPU-generated ESP-PPQ test vectors:
`Model::test()` expected int8 `score0 = -102` and received `127` at
`[0,0,0,0]`. It stopped with `MODEL_SELFTEST FAIL`. This comparison concerns
numeric execution, not cat or deer recognition accuracy. QEMU scores from
this setup must not be used to evaluate classifier accuracy or judge the
retained deer artifact. Use the restored `.pt` checkpoint with the CPU
evaluator for the current image-dataset evaluation.

The application builds, reads host RGB records, verifies their hashes, and
can invoke a model, but successful execution is insufficient to establish
numerical correctness. Keep this project as a diagnostic path until the
golden-vector comparison passes. No QEMU or ESP-DL vendor kernels were changed.

This camera-free ESP-IDF application runs the unchanged
`deer_classifier/artifacts/deer.espdl` using the same `DeerDetector` wrapper as
the physical camera smoke test. The intended path uses Espressif's ESP32-S3
QEMU to execute the compiled Xtensa kernels, including S3 SIMD instructions;
the failed oracle above prevents treating that execution as validated.
Dataset images come from a
read-only host file rather than a camera. This path needs no original `.pt`
checkpoint, training environment, camera, or USB-connected board.

Build with ESP-IDF 5.4.x / 5.5.x, target `esp32s3`:

```powershell
.\idf-local.ps1 build
```

The local wrapper uses the ignored repository `.tools` installation. For a
normal installed ESP-IDF terminal, use `idf.py set-target esp32s3` then
`idf.py build`. The manifest pins ESP-DL 3.3.14. The shared wrapper handles
normalization, centered letterbox fill 114, input quantization, and ESPDet box
decoding through the camera app's shared implementation. Candidate scores below 0.10 are filtered;
a reported zero means no retained deer box reached that floor.

## Input protocol

Place `frames.bin` in QEMU's working directory. Its binary format is:

1. Eight ASCII bytes `DEERDS01`.
2. A little-endian unsigned 32-bit record count, from 1 through 100,000.
3. For every image: little-endian unsigned 32-bit `id`, `width`, `height`, then
   exactly `width * height * 3` bytes of interleaved RGB888 pixels in row order.

IDs must be consecutive from zero. Width must be 1–640 and height 1–480.
Use source images decoded to RGB, optionally reduced with aspect ratio
preserved; do not crop or letterbox before writing them. The device wrapper
applies the same 224 × 224 preprocessing used for camera frames. Record any
host resize method and dimensions when reporting results. One image buffer
is allocated in PSRAM at a time. Extra trailing data, missing records,
allocation failure, and invalid inference scores fail the entire run.

The host preparation/evaluation script owns image labels and computes
image-level accuracy from the returned scores. This firmware never reads
labels and does not alter the model. A synthetic neutral image can verify
invocation but cannot establish recognition accuracy.

## QEMU execution

Use the official Espressif QEMU fork with the `esp32s3` machine, UART serial
output, **2 MB emulated PSRAM**, and native Xtensa semihosting enabled. Merge
the firmware's `build/flash_args` into a 4 MB flash image with the installed
ESP-IDF esptool, then run QEMU from the directory containing `frames.bin`:

```text
qemu-system-xtensa -machine esp32s3 -m 2M -nographic -monitor none -serial stdio -semihosting -drive file=<absolute-merged-flash-image>,if=mtd,format=raw
```

The application exits QEMU with status zero after printing `END`, or nonzero
after an error. The default configuration disables watchdogs for emulation,
uses a UART console, and hashes frame pixels with software SHA-256. QEMU
timings are emulator measurements and do not estimate board latency or power.

On Windows, native QEMU `SYS_open` needs the host `O_BINARY` flag so byte
0x1A and line endings remain unchanged. `DEER_EVAL_HOST_WINDOWS=y` is the
default; disable it in menuconfig on a Linux/macOS host.

ESP-IDF's `esp_vfs_semihost_register` implements OpenOCD/ARM conventions,
which its own `openocd_semihosting.h` identifies as incompatible with Xtensa
QEMU. `qemu_input.hpp` instead uses QEMU's native, documented `SIMCALL` ABI
for fixed-file open/read/close and process exit. It does not emulate any neural
network operations or unpack/rewrite model weights. The filename is relative
to the QEMU process's host working directory; no `/host` VFS mount is used.

## Output and validation

```text
BOOT dataset_eval model_bytes=499712 sha256=<model-file-sha256>
MODEL_SELFTEST SKIP
READY count=2 score_floor=0.1000
RESULT id=0 score=0.00000000 rgb_sha256=<raw-rgb-sha256> infer_ms=1234.567
RESULT id=1 score=0.91234567 rgb_sha256=<raw-rgb-sha256> infer_ms=1234.567
END count=2
```

Values above are examples. Passing the numerical oracle is a prerequisite;
it currently fails. Once numerical execution has been validated, an intact
evaluation run additionally requires the expected model SHA-256,
each expected ID exactly once, matching raw-RGB hashes, a complete `END`, no
errors/panics/resets, and QEMU exit status zero. The retained model has no
embedded golden test vectors, hence `MODEL_SELFTEST SKIP`. The intended
evaluation would measure the compiled quantized model on those image files;
current QEMU outputs cannot establish that result. This path does not test the
OV5640 sensor path, physical printed images, real-board memory/timing, or
generalization to a future deployment scene.

The first two frames print `TENSOR` diagnostics for the quantized input before
inference and all six outputs afterward: dtype, exponent, logical element
count, signed int8 range, sum, FNV-1a checksum, and endpoint saturation counts.
These statistics diagnose numeric or export problems and are not accuracy
metrics. The camera application leaves this optional tracing disabled.

For a separate export containing numerical golden test vectors, configure
`-D DEER_EVAL_MODEL_FILE=<absolute-model-path>` and
`-D DEER_EVAL_VERIFY_GOLDEN=ON`. This CMake option runs `Model::test()` before
the model is minimized. It avoids a global sdkconfig change. The model's real
size and hash are still printed at boot. A cat-model oracle checks numerical
execution only and must never be reported as the retained deer model's
recognition accuracy. Restore the default artifact path and set the option
to `OFF` before evaluating deer images with the retained model.

References: [Espressif QEMU setup](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/tools/qemu.html),
[ESP32-S3 PSRAM arguments](https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/esp32s3/README.md),
[native Xtensa semihosting implementation](https://github.com/espressif/qemu/blob/esp-develop/target/xtensa/xtensa-semi.c),
[ESP32-S3 SIMD emulation](https://github.com/espressif/qemu/blob/esp-develop/target/xtensa/translate_tie_esp32s3.c).
