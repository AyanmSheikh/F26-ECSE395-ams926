#pragma once

#include <cstdint>
#include <cmath>

// Lightweight firmware-side 2-of-3 temporal confirmation.
class TemporalDeerGate {
 public:
  static constexpr uint8_t kWindow = 3;
  static constexpr uint8_t kRequired = 2;
  static constexpr float kThreshold = 0.85f;

  explicit TemporalDeerGate(float threshold = kThreshold) : threshold_(threshold) {}

  bool update(bool frame_valid, float deer_score) {
    if (!frame_valid || !std::isfinite(deer_score) || deer_score < 0.0f || deer_score > 1.0f ||
        !std::isfinite(threshold_) || threshold_ < 0.0f || threshold_ > 1.0f) {
      reset();
      return false;
    }

    history_ = ((history_ << 1) | (deer_score >= threshold_ ? 1u : 0u)) & 0x7u;
    uint8_t hits = 0;
    for (uint8_t i = 0; i < kWindow; ++i) {
      hits += (history_ >> i) & 1u;
    }
    return hits >= kRequired;
  }

  void reset() { history_ = 0; }

 private:
  float threshold_;
  uint8_t history_ = 0;
};
