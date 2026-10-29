#pragma once

#include <algorithm>
#include <cmath>
#include <cinttypes>
#include <cstdio>
#include <memory>
#include <string>
#include <vector>

#include "dl_detect_espdet_postprocessor.hpp"
#include "dl_image_preprocessor.hpp"
#include "dl_model_base.hpp"
#include "sdkconfig.h"

extern const uint8_t deer_model_data[] asm("_binary_deer_espdl_start");

// One raw ESPDet-Pico export, not Espressif's packed cat/example model bundle.
class DeerDetector {
 public:
  bool initialize() {
    // Preserve scarce PSRAM by reading weights from flash. Zero internal arena
    // asks ESP-DL to allocate the model arena in PSRAM when it is available.
    model_.reset(new dl::Model(reinterpret_cast<const char*>(deer_model_data),
                               fbs::MODEL_LOCATION_IN_FLASH_RODATA, 0,
                               dl::MEMORY_MANAGER_GREEDY, nullptr, false));
    const auto& inputs = model_->get_inputs();
    if (inputs.size() != 1 || inputs.begin()->second->shape != std::vector<int>({1, 224, 224, 3}) ||
        inputs.begin()->second->dtype != dl::DATA_TYPE_INT8 || model_->get_outputs().size() != 6) {
      std::printf("ERROR n=0 reason=model_shape present=0\n");
      return false;
    }
    // ESP-DL's ESPDet postprocessor accesses these names directly. Validate
    // every stage before inference so an incompatible replacement export
    // cannot cause a null lookup or incorrect box-buffer indexing.
    const auto& outputs = model_->get_outputs();
    for (int stage = 0; stage < 3; ++stage) {
      const int side = 224 / (8 << stage);
      const auto box = outputs.find("box" + std::to_string(stage));
      const auto score = outputs.find("score" + std::to_string(stage));
      if (box == outputs.end() || score == outputs.end() ||
          box->second->shape != std::vector<int>({1, side, side, 4}) ||
          score->second->shape != std::vector<int>({1, side, side, 1}) ||
          box->second->dtype != dl::DATA_TYPE_INT8 || score->second->dtype != dl::DATA_TYPE_INT8) {
        std::printf("ERROR n=0 reason=model_output_contract present=0\n");
        return false;
      }
    }
#if defined(CONFIG_DEER_RUN_MODEL_SELFTEST) || defined(DEER_EVAL_VERIFY_GOLDEN)
    const auto status = model_->test();
    std::printf("MODEL_SELFTEST %s\n", status == ESP_OK ? "PASS" : "FAIL");
    if (status != ESP_OK) return false;
#else
    std::printf("MODEL_SELFTEST SKIP\n");
#endif
    model_->minimize();
    preprocessor_.reset(new dl::image::ImagePreprocessor(model_.get(), {0, 0, 0}, {255, 255, 255}));
    preprocessor_->enable_letterbox({114, 114, 114});
    postprocessor_.reset(new dl::detect::ESPDetPostProcessor(
        model_.get(), preprocessor_.get(), 0.10f, 0.70f, 10,
        {{8, 8, 4, 4}, {16, 16, 8, 8}, {32, 32, 16, 16}}));
    return true;
  }

  // ESP-DL's model runner is fail-fast on allocation/operator errors. This
  // method validates returned scores; startup/runtime panics cannot emit a
  // successful deer event. An empty detection list is a valid zero score.
  bool infer(const dl::image::img_t& image, float& score, bool trace_tensors = false) {
    preprocessor_->preprocess(image);
    if (trace_tensors) {
      for (const auto& input : model_->get_inputs()) print_tensor("input", input.first.c_str(), input.second);
    }
    model_->run();
    if (trace_tensors) {
      for (const auto& output : model_->get_outputs()) print_tensor("output", output.first.c_str(), output.second);
    }
    postprocessor_->clear_result();
    postprocessor_->postprocess();
    score = 0.0f;
    for (const auto& detection : postprocessor_->get_result(image.width, image.height)) {
      if (!std::isfinite(detection.score) || detection.score < 0 || detection.score > 1) return false;
      if (detection.category == 0) score = std::max(score, detection.score);
    }
    return true;
  }

 private:
  static void print_tensor(const char* phase, const char* name, dl::TensorBase* tensor) {
    size_t elements = 1;
    for (const auto dimension : tensor->shape) elements *= dimension;
    if (tensor->dtype != dl::DATA_TYPE_INT8) {
      std::printf("TENSOR phase=%s name=%s dtype=%d elements=%u unsupported_stats=1\n",
                  phase, name, static_cast<int>(tensor->dtype), static_cast<unsigned>(elements));
      return;
    }
    const int8_t* values = tensor->get_element_ptr<int8_t>();
    int minimum = 127, maximum = -128;
    int64_t sum = 0;
    uint32_t checksum = 2166136261u;
    size_t clipped_low = 0, clipped_high = 0;
    for (size_t i = 0; i < elements; ++i) {
      const int value = values[i];
      minimum = std::min(minimum, value);
      maximum = std::max(maximum, value);
      sum += value;
      checksum = (checksum ^ static_cast<uint8_t>(values[i])) * 16777619u;
      clipped_low += value == -128;
      clipped_high += value == 127;
    }
    std::printf("TENSOR phase=%s name=%s dtype=%d exponent=%d elements=%u min=%d max=%d sum=%" PRId64
                " fnv1a=%08" PRIx32 " clipped_low=%u clipped_high=%u\n",
                phase, name, static_cast<int>(tensor->dtype), tensor->get_exponent(),
                static_cast<unsigned>(elements), minimum, maximum, sum, checksum,
                static_cast<unsigned>(clipped_low), static_cast<unsigned>(clipped_high));
  }

  // Destruction is the reverse of declaration: processors before their model.
  std::unique_ptr<dl::Model> model_;
  std::unique_ptr<dl::image::ImagePreprocessor> preprocessor_;
  std::unique_ptr<dl::detect::ESPDetPostProcessor> postprocessor_;
};
