#include <cinttypes>
#include <cstdio>
#include <cstring>
#include <limits>

#include "driver/gpio.h"
#include "esp_camera.h"
#include "esp_heap_caps.h"
#include "esp_psram.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "dl_image_jpeg.hpp"
#include "deer_detector.hpp"
#include "../../../temporal_gate.hpp"

namespace {
constexpr float kThreshold = CONFIG_DEER_THRESHOLD_PERCENT / 100.0f;

bool run_gate_selftest() {
  TemporalDeerGate test(kThreshold);
  bool passed = !test.update(true, 1.0f);
  passed &= test.update(true, 1.0f);
  passed &= test.update(true, 0.0f);
  passed &= !test.update(true, 0.0f);
  test.reset();
  passed &= !test.update(true, 1.0f);
  passed &= !test.update(true, std::numeric_limits<float>::quiet_NaN());
  passed &= !test.update(true, 1.0f);
  passed &= test.update(true, 1.0f);
  passed &= !test.update(false, 0.0f);
  passed &= !test.update(true, 1.0f);
  std::printf("GATE_SELFTEST %s\n", passed ? "PASS" : "FAIL");
  return passed;
}

bool run_inference_smoke(DeerDetector& detector) {
  constexpr size_t bytes = 224 * 224 * 3;
  void* pixels = heap_caps_aligned_alloc(16, bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!pixels) {
    std::printf("INFERENCE_SELFTEST FAIL reason=allocation\n");
    return false;
  }
  std::memset(pixels, 114, bytes);
  const dl::image::img_t blank{pixels, 224, 224, dl::image::DL_IMAGE_PIX_TYPE_RGB888};
  float score = 0;
  const bool passed = detector.infer(blank, score);
  heap_caps_free(pixels);
  std::printf("INFERENCE_SELFTEST %s score=%.4f\n", passed ? "PASS" : "FAIL", score);
  return passed;
}

bool check_camera_pins() {
#ifndef CONFIG_DEER_PINS_CONFIRMED
  std::printf("ERROR n=0 reason=pins_unconfigured present=0\n");
  std::printf("Set Deer camera smoke test GPIOs in idf.py menuconfig before flashing.\n");
  return false;
#endif
  const int pins[] = {CONFIG_DEER_PIN_XCLK, CONFIG_DEER_PIN_SDA, CONFIG_DEER_PIN_SCL,
                      CONFIG_DEER_PIN_D0, CONFIG_DEER_PIN_D1, CONFIG_DEER_PIN_D2, CONFIG_DEER_PIN_D3,
                      CONFIG_DEER_PIN_D4, CONFIG_DEER_PIN_D5, CONFIG_DEER_PIN_D6, CONFIG_DEER_PIN_D7,
                      CONFIG_DEER_PIN_VSYNC, CONFIG_DEER_PIN_HREF, CONFIG_DEER_PIN_PCLK,
                      CONFIG_DEER_PIN_PWDN, CONFIG_DEER_PIN_RESET};
  for (size_t i = 0; i < sizeof(pins) / sizeof(pins[0]); ++i) {
    const int pin = pins[i];
    if (i >= 14 && pin == -1) continue;  // Optional PWDN and RESET only.
    if (!GPIO_IS_VALID_GPIO(pin) || pin == 19 || pin == 20 || pin == 7 || pin == 21 || pin == 45 ||
        (pin >= 26 && pin <= 32)) {
      std::printf("ERROR n=0 reason=invalid_or_reserved_gpio gpio=%d present=0\n", pin);
      return false;
    }
    if ((i < 3 || i >= 14) && !GPIO_IS_VALID_OUTPUT_GPIO(pin)) {
      std::printf("ERROR n=0 reason=camera_output_gpio gpio=%d present=0\n", pin);
      return false;
    }
    for (size_t j = 0; j < i; ++j) {
      if (pins[j] == pin) {
        std::printf("ERROR n=0 reason=duplicate_gpio gpio=%d present=0\n", pin);
        return false;
      }
    }
  }
  return true;
}

void initialize_feather_power() {
  // Adafruit's TFT Feather gates the TFT and I2C pull-up rail with GPIO21.
  // Keep the TFT deselected and its backlight off while using the camera.
  gpio_set_level(GPIO_NUM_7, 1);
  gpio_set_direction(GPIO_NUM_7, GPIO_MODE_OUTPUT);
  gpio_set_level(GPIO_NUM_45, 0);
  gpio_set_direction(GPIO_NUM_45, GPIO_MODE_OUTPUT);
  gpio_set_level(GPIO_NUM_21, 1);
  gpio_set_direction(GPIO_NUM_21, GPIO_MODE_OUTPUT);
  vTaskDelay(pdMS_TO_TICKS(20));
}

esp_err_t initialize_camera() {
  camera_config_t config{};
  config.pin_pwdn = CONFIG_DEER_PIN_PWDN;
  config.pin_reset = CONFIG_DEER_PIN_RESET;
  config.pin_xclk = CONFIG_DEER_PIN_XCLK;
  config.pin_sccb_sda = CONFIG_DEER_PIN_SDA;
  config.pin_sccb_scl = CONFIG_DEER_PIN_SCL;
  config.pin_d0 = CONFIG_DEER_PIN_D0;
  config.pin_d1 = CONFIG_DEER_PIN_D1;
  config.pin_d2 = CONFIG_DEER_PIN_D2;
  config.pin_d3 = CONFIG_DEER_PIN_D3;
  config.pin_d4 = CONFIG_DEER_PIN_D4;
  config.pin_d5 = CONFIG_DEER_PIN_D5;
  config.pin_d6 = CONFIG_DEER_PIN_D6;
  config.pin_d7 = CONFIG_DEER_PIN_D7;
  config.pin_vsync = CONFIG_DEER_PIN_VSYNC;
  config.pin_href = CONFIG_DEER_PIN_HREF;
  config.pin_pclk = CONFIG_DEER_PIN_PCLK;
  config.xclk_freq_hz = CONFIG_DEER_CAMERA_XCLK_MHZ * 1000000;
  config.ledc_timer = LEDC_TIMER_0;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.pixel_format = PIXFORMAT_JPEG;
#ifdef CONFIG_DEER_CAMERA_VGA
  config.frame_size = FRAMESIZE_VGA;
#else
  config.frame_size = FRAMESIZE_QVGA;
#endif
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  return esp_camera_init(&config);
}

void clear_on_error(TemporalDeerGate& gate, bool& present, unsigned n, const char* reason) {
  gate.update(false, 0);
  std::printf("ERROR n=%u reason=%s present=0\n", n, reason);
  if (present) std::printf("DEER_CLEARED n=%u\n", n);
  present = false;
}
}  // namespace

extern "C" void app_main() {
  setvbuf(stdout, nullptr, _IONBF, 0);
  // Let a host monitor reconnect after USB reset; no indefinite wait for USB.
  vTaskDelay(pdMS_TO_TICKS(1500));
  std::printf("BOOT deer_camera_smoke model_bytes=%u sha256=%s\n",
              static_cast<unsigned>(DEER_MODEL_BYTES), DEER_MODEL_SHA256);
  if (!run_gate_selftest()) return;
  if (!check_camera_pins()) return;
  initialize_feather_power();
  if (!esp_psram_is_initialized() || esp_psram_get_size() < 2 * 1024 * 1024) {
    std::printf("ERROR n=0 reason=psram_required present=0\n");
    return;
  }
  const auto camera_status = initialize_camera();
  if (camera_status != ESP_OK) {
    std::printf("ERROR n=0 reason=camera_init code=%d present=0\n", camera_status);
    return;
  }
  sensor_t* sensor = esp_camera_sensor_get();
  if (!sensor || sensor->id.PID != OV5640_PID) {
    std::printf("ERROR n=0 reason=expected_ov5640 present=0\n");
    esp_camera_deinit();
    return;
  }
#ifdef CONFIG_DEER_CAMERA_HMIRROR
  sensor->set_hmirror(sensor, 1);
#endif
#ifdef CONFIG_DEER_CAMERA_VFLIP
  sensor->set_vflip(sensor, 1);
#endif
  DeerDetector detector;
  if (!detector.initialize()) {
    esp_camera_deinit();
    return;
  }
  // This tests invocation and finite output only. There are no golden vectors
  // in the current export, and a synthetic blank cannot test recognition.
  if (!run_inference_smoke(detector)) {
    std::printf("ERROR n=0 reason=inference_selftest present=0\n");
    esp_camera_deinit();
    return;
  }
  // Discard initial frames while automatic exposure settles. No gate updates.
  for (unsigned i = 0; i < 8; ++i) {
    camera_fb_t* frame = esp_camera_fb_get();
    if (frame) esp_camera_fb_return(frame);
    vTaskDelay(pdMS_TO_TICKS(100));
  }
  TemporalDeerGate gate(kThreshold);
  bool present = false;
  std::printf("READY model_bytes=%u threshold=%.4f window=3 required=2 width=224 height=224\n",
              static_cast<unsigned>(DEER_MODEL_BYTES), kThreshold);
  unsigned n = 0;
  while (true) {
    ++n;
    const int64_t start = esp_timer_get_time();
    camera_fb_t* frame = esp_camera_fb_get();
    const int64_t captured = esp_timer_get_time();
    if (!frame) {
      clear_on_error(gate, present, n, "camera_capture");
      vTaskDelay(pdMS_TO_TICKS(500));
      continue;
    }
    if (frame->format != PIXFORMAT_JPEG || frame->width > 640 || frame->height > 480 || frame->len == 0) {
      esp_camera_fb_return(frame);
      clear_on_error(gate, present, n, "frame_format");
      vTaskDelay(pdMS_TO_TICKS(500));
      continue;
    }
    const dl::image::jpeg_img_t jpeg{frame->buf, frame->len};
    dl::image::img_t image = dl::image::sw_decode_jpeg(jpeg, dl::image::DL_IMAGE_PIX_TYPE_RGB888);
    const bool image_valid = image.data && image.width == frame->width && image.height == frame->height;
    esp_camera_fb_return(frame);
    const int64_t decoded = esp_timer_get_time();
    if (!image_valid) {
      heap_caps_free(image.data);
      clear_on_error(gate, present, n, "jpeg_decode");
      vTaskDelay(pdMS_TO_TICKS(500));
      continue;
    }
    float score = 0;
    const bool inference_valid = detector.infer(image, score);
    heap_caps_free(image.data);
    const int64_t inferred = esp_timer_get_time();
    if (!inference_valid) {
      clear_on_error(gate, present, n, "inference_score");
      vTaskDelay(pdMS_TO_TICKS(500));
      continue;
    }
    const bool next_present = gate.update(true, score);
    std::printf("FRAME n=%u score=%.4f present=%u capture_ms=%.2f decode_ms=%.2f infer_ms=%.2f total_ms=%.2f psram_free=%u\n",
                n, score, static_cast<unsigned>(next_present), (captured - start) / 1000.0,
                (decoded - captured) / 1000.0, (inferred - decoded) / 1000.0,
                (inferred - start) / 1000.0,
                static_cast<unsigned>(heap_caps_get_free_size(MALLOC_CAP_SPIRAM)));
    if (next_present && !present) std::printf("DEER_DETECTED n=%u score=%.4f\n", n, score);
    if (!next_present && present) std::printf("DEER_CLEARED n=%u\n", n);
    present = next_present;
    // Always yield to the idle task even if the configured pause is zero.
    vTaskDelay(pdMS_TO_TICKS(CONFIG_DEER_FRAME_INTERVAL_MS) + 1);
  }
}
