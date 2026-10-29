#include <cinttypes>
#include <cmath>
#include <cstdio>
#include <cstring>

#include "deer_detector.hpp"
#include "esp_heap_caps.h"
#include "esp_psram.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "mbedtls/sha256.h"
#include "qemu_input.hpp"

namespace {
[[noreturn]] void fail(const char* reason, uint32_t id = 0) {
  std::printf("ERROR id=%" PRIu32 " reason=%s\n", id, reason);
  std::fflush(stdout);
  vTaskDelay(pdMS_TO_TICKS(100));
  qemu_input::exit(1);
}

bool hash_rgb(const void* data, size_t bytes, char (&hex)[65]) {
  uint8_t digest[32];
  if (mbedtls_sha256(static_cast<const uint8_t*>(data), bytes, digest, 0) != 0) return false;
  constexpr char alphabet[] = "0123456789abcdef";
  for (size_t i = 0; i < sizeof(digest); ++i) {
    hex[2 * i] = alphabet[digest[i] >> 4];
    hex[2 * i + 1] = alphabet[digest[i] & 15];
  }
  hex[64] = '\0';
  return true;
}
}  // namespace

extern "C" void app_main() {
  setvbuf(stdout, nullptr, _IONBF, 0);
  std::printf("BOOT dataset_eval model_bytes=%u sha256=%s\n",
              static_cast<unsigned>(DEER_MODEL_BYTES), DEER_MODEL_SHA256);
  if (!esp_psram_is_initialized()) fail("psram_unavailable");
  const int fd = qemu_input::open();
  if (fd < 0) fail("frames_open");
  char magic[8];
  uint32_t count = 0;
  if (!qemu_input::read_exact(fd, magic, sizeof(magic)) || std::memcmp(magic, "DEERDS01", 8) != 0 ||
      !qemu_input::read_u32(fd, count) || count == 0 || count > 100000) fail("dataset_header");
  DeerDetector detector;
  if (!detector.initialize()) fail("model_initialize");
  std::printf("READY count=%" PRIu32 " score_floor=0.1000\n", count);
  for (uint32_t index = 0; index < count; ++index) {
    uint32_t id, width, height;
    if (!qemu_input::read_u32(fd, id) || !qemu_input::read_u32(fd, width) || !qemu_input::read_u32(fd, height))
      fail("record_header", index);
    if (id != index || width == 0 || width > 640 || height == 0 || height > 480) fail("record_dimensions_or_id", index);
    const size_t bytes = static_cast<size_t>(width) * height * 3;
    void* pixels = heap_caps_aligned_alloc(16, bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!pixels) fail("frame_allocation", id);
    if (!qemu_input::read_exact(fd, pixels, bytes)) fail("record_pixels", id);
    char rgb_hash[65];
    if (!hash_rgb(pixels, bytes, rgb_hash)) fail("frame_sha256", id);
    const dl::image::img_t image{pixels, static_cast<uint16_t>(width), static_cast<uint16_t>(height),
                                dl::image::DL_IMAGE_PIX_TYPE_RGB888};
    float score = 0;
    const int64_t start = esp_timer_get_time();
    const bool valid = detector.infer(image, score, index < 2);
    const int64_t stop = esp_timer_get_time();
    heap_caps_free(pixels);
    if (!valid || !std::isfinite(score) || score < 0 || score > 1) fail("inference_score", id);
    std::printf("RESULT id=%" PRIu32 " score=%.8f rgb_sha256=%s infer_ms=%.3f\n",
                id, score, rgb_hash, (stop - start) / 1000.0);
    vTaskDelay(1);
  }
  uint8_t extra;
  const int32_t trailing = qemu_input::syscall(3, fd, reinterpret_cast<int32_t>(&extra), 1);
  if (trailing != 0) fail("trailing_data_or_read_error");
  if (qemu_input::close(fd) != 0) fail("frames_close");
  std::printf("END count=%" PRIu32 "\n", count);
  std::fflush(stdout);
  vTaskDelay(pdMS_TO_TICKS(100));
  qemu_input::exit(0);
}
