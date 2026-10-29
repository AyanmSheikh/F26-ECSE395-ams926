# OV5640 printed-deer smoke test

This standalone ESP-IDF application embeds the existing experimental
`deer_classifier/artifacts/deer.espdl` detector and prints a confirmed deer
signal over USB serial. It is the first hardware milestone before adding the
light, sound, or image-saving behavior. The current model has weak historical
validation results; a successful printed-image test is a smoke test, not proof
of field accuracy.

The target is the **Adafruit ESP32-S3 TFT Feather, 4 MB flash / 2 MB PSRAM**
with the **Adafruit OV5640 parallel camera breakout**. The older Feather ESP32
V2 used in the lab folders cannot run this ESP32-S3 model artifact. The camera
requires its parallel data and timing wires as well as SCCB control; connecting
only SDA/SCL does not transfer camera images.

## Configure the real wiring first

No camera wiring was recorded in the handoff. Run `idf.py menuconfig`, open
**Deer camera smoke test**, enter the actual MCU GPIO numbers for XCLK, SIOD,
SIOC, VSYNC, HREF, PCLK, and the eight data lines, then enable **I have entered
and checked my actual OV5640 DVP wiring**. PWDN and RESET may remain `-1` only
if the breakout holds them at the inactive levels. The unconfigured project
builds, but deliberately prints `ERROR ... reason=pins_unconfigured` and stops.

The camera's **D2 through D9** correspond to the driver's **D0 through D7**
respectively. Enter the MCU GPIO numbers from the Feather pinout, not labels
such as A0 or D5. Check the TFT, SPI, I2C, boot, and power circuitry before
assigning pins. This application does not initialize the TFT. GPIO19/20 are
reserved for the USB serial console; GPIO26–32 are rejected because they are
reserved for the module's flash/PSRAM. Duplicate or invalid pins also stop
startup. These checks cannot verify external wiring or that a pin is exposed
on this particular board.

An opt-in proposed mapping is included in
`sdkconfig.feather_ov5640.defaults`. It connects camera D2–D9 to Feather
A0/A1/A2/A3/A4/A5/D5/D6; PC to D9; VS to D10; HS to D11; XC to D12; SDA/SCL
to the corresponding Feather SDA/SCL pins. Connect breakout power to 3.3 V
and GND and keep its external-clock jumper at **EXT**. This mapping is derived
from the [official board definitions](https://github.com/espressif/arduino-esp32/blob/master/variants/adafruit_feather_esp32s3_tft/pins_arduino.h),
and must match the physical wires before confirmation is enabled.

To load that proposal into a fresh configuration, use this first command
instead of the plain `set-target` below, then inspect it in menuconfig:

```powershell
idf.py -D "SDKCONFIG_DEFAULTS=sdkconfig.defaults;sdkconfig.feather_ov5640.defaults" set-target esp32s3
```

The firmware turns on the Feather's shared I2C/TFT power rail at GPIO21,
holds TFT CS (GPIO7) high, and disables its backlight (GPIO45). These three
GPIOs are also reserved by the pin validator. The TFT is otherwise idle.

Use the manufacturer references to verify the exact breakout, signal naming,
and power connections:

- [Feather pinouts](https://learn.adafruit.com/adafruit-esp32-s3-tft-feather/pinouts)
- [OV5640 breakout guide](https://learn.adafruit.com/adafruit-ov5640-camera-breakout)

## Build and connect

Install **ESP-IDF 5.4.x or 5.5.x** with the ESP32-S3 toolchain and open an
ESP-IDF terminal. The first build downloads the exact component versions in
`main/idf_component.yml`: ESP-DL 3.3.14 and esp32-camera 2.1.3.

This Windows workspace already has ESP-IDF 5.4.2 and the ESP32-S3 compiler in
the ignored root `.tools/` directory. From this folder, `./idf-local.ps1`
accepts the same arguments as `idf.py`, for example `./idf-local.ps1 build`.
It activates tools only in its process and does not alter global settings.
Use the full SDKCONFIG_DEFAULTS command above with `./idf-local.ps1` to start
a fresh configuration with the proposed wiring. Inspect/confirm the pins in
`./idf-local.ps1 menuconfig` before building firmware for actual use.

From this folder:

```powershell
idf.py set-target esp32s3
idf.py menuconfig
idf.py build
idf.py -p COM5 flash monitor
```

Replace `COM5` with the connected board's port. Exit the IDF monitor with
Ctrl+]. The USB serial/JTAG console is selected by default. If the board does
not enumerate for flashing, use its documented BOOT/RESET procedure. Flashing
this standalone ESP-IDF application replaces the currently installed board
application and may replace the UF2 bootloader layout; retain any board files
you need and use Adafruit's restore instructions to return to CircuitPython.

The 4 MB partition layout has one application slot, including the model.
There is no OTA or filesystem. The model file's size and SHA-256 are computed
at build time and printed at boot so a log identifies the actual artifact.

The full proposed-wiring configuration compiled and linked with ESP-IDF 5.4.2
on Windows. Its application binary is 1,853,872 bytes (about 1.77 MiB),
including the unchanged 499,712-byte model, leaving 55% of the application
partition free. The unconfigured build can optimize out the unreachable camera
and model path, so its smaller size is not a deployment measurement. Runtime
RAM, sensor startup, inference timing and recognition remain unmeasured until
the board is connected. No firmware was flashed during development.

## Run the physical check

1. Connect only the camera and USB for this milestone. Put a blank scene or
   blank sheet in view. Wait for `READY`, then confirm repeated `FRAME` lines
   with `present=0` and no `ERROR` or reset messages.
2. Show a well-lit, focused printed deer image upright to the camera, initially
   occupying a substantial part of the field of view. Confirm
   `DEER_DETECTED` and repeated `FRAME ... present=1`. It takes two confident
   frames in the three-frame window to confirm; a single high score is
   insufficient.
3. Remove the deer print. Confirm `DEER_CLEARED` and that `present` returns
   to zero within three valid low-score frames.
4. Repeat with a different deer print and an empty or non-deer print. Save the
   serial log along with distance, lighting, focus, orientation, and print size.

For an evidence log and automatic pass/fail, exit the serial monitor, open a
Python terminal in `deer_classifier/`, and run:

```powershell
python -m pip install -r requirements-smoke.txt
python smoke_check.py --port COM5
```

Press the board's RESET button when prompted. The recorder reads continuously
through the scene-change prompts. Each phase waits three settling frames and
measures ten frames. It requires no confirmed detections in the baseline and
clear phases, at least two confirmed frames in the deer phase, and no errors,
resets, frame gaps or gate inconsistencies. JSONL evidence is saved under
`artifacts/smoke/`. Recheck a saved log with `python smoke_check.py --replay
artifacts/smoke/FILE.jsonl`. These short phases establish a demonstration,
not statistical field accuracy. Use additional deer/non-deer prints to check
that the model responds to deer content rather than any sheet of paper.

With this workspace's local IDF Python, pyserial is already installed:

```powershell
& ./.tools/idf-tools/python_env/idf5.4_py3.12_env/Scripts/python.exe ./deer_classifier/smoke_check.py --port COM5
```

Run that last command from the repository root. Replace COM5 with the board's
port. No physical test has run on this computer because no board is connected.

Typical output format (illustrative values):

```text
BOOT deer_camera_smoke model_bytes=499712 sha256=...
GATE_SELFTEST PASS
MODEL_SELFTEST SKIP
INFERENCE_SELFTEST PASS score=0.0000
READY model_bytes=499712 threshold=0.8500 window=3 required=2 width=224 height=224
FRAME n=1 score=0.9100 present=0 capture_ms=... decode_ms=... infer_ms=... total_ms=... psram_free=...
FRAME n=2 score=0.9300 present=1 capture_ms=... decode_ms=... infer_ms=... total_ms=... psram_free=...
DEER_DETECTED n=2 score=0.9300
```

`score` is the largest class-0 deer-box confidence, not a calibrated deer
probability. Candidate boxes below 0.10 are filtered before reporting (the
floor drops to the gate threshold if that is set below 0.10); zero can mean no
box reached that floor. The gate threshold starts at 0.85 to match the
handoff and is configurable in menuconfig. Scores printed continuously help
diagnose a weak model or unsuitable lighting. Changing a threshold to make a
print trigger does not establish an acceptable false-positive rate.

Camera, decoding, invalid-score, or frame-format errors clear the confirmation
history and print `ERROR ... present=0`. A fatal ESP-DL allocation/operator
failure may panic or reset the device; a session containing errors or resets
does not pass the smoke test. `READY` means initialization completed, not that
recognition has passed.

## Image path and memory

The default camera configuration captures **320 × 240 JPEG**, one framebuffer
in PSRAM, at the camera driver's default 20 MHz XCLK. Adafruit documents a
nominal 24 MHz external clock; the sensor permits both, and menuconfig exposes
the frequency for real-camera verification. Initial frames are discarded for
exposure settling.
ESP-DL's software decoder creates explicit RGB888 pixels; its preprocessor
preserves aspect ratio, centers the image in a 224 × 224 letterbox filled with
RGB (114, 114, 114), divides channels by 255, and applies model int8
quantization. ESPDet's three detection stages use strides 8/16/32 and the
upstream box-decoding parameters. The largest deer score feeds the shared
`TemporalDeerGate` in `../../temporal_gate.hpp`.

Weights stay in flash (`param_copy=false`) to reduce PSRAM use. The QVGA RGB
buffer alone uses 230,400 bytes and is freed after every inference. Optional
VGA JPEG capture increases that buffer to 921,600 bytes and may not fit with
the model on this 2 MB board. Keep QVGA for the initial check. The log reports
free PSRAM and camera/decode/inference latency; latency and current have not
been measured on this physical unit.

**Run ESP-DL embedded input/output test vectors at boot** is an optional
menuconfig setting. Enable it only if that export contains test vectors. It
runs `Model::test()` before normal preprocessing; a failure stops startup.
`MODEL_SELFTEST PASS` verifies those stored tensors, not the camera path or
deer recognition. With this option disabled, `MODEL_SELFTEST SKIP` is explicit.
The currently checked-in artifact contains no embedded test vectors, so leave
this setting disabled for that model.

`GATE_SELFTEST PASS` checks the actual C++ gate using known hit, clear, invalid
frame, and NaN sequences. `INFERENCE_SELFTEST PASS` runs the deployed model on
a synthetic RGB (114,114,114) image and checks that inference returns a finite
valid score. That is an invocation check without a golden numerical target;
it does not establish camera decoding or deer recognition. Neither self-test
updates the live camera's gate history.

The implementation follows Espressif's
[ESP-Detection template](https://github.com/espressif/esp-detection/blob/28de5902a357d99dd9a5db0f52905255641c5a78/deploy/espdet_model_template/espdet_detect.cpp),
the [ESP-DL model-loading API](https://docs.espressif.com/projects/esp-dl/en/latest/tutorials/how_to_load_test_profile_model.html),
and the [camera driver](https://github.com/espressif/esp32-camera/tree/v2.1.3).
