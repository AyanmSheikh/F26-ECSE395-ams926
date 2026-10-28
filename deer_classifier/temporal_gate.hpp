#pragma once

#include <cstdint>

// Lightweight firmware-side 2-of-3 temporal confirmation.
class TemporalDeerGate {
 public:
  static constexpr uint8_t kWindow = 3;
  static constexpr uint8_t kRequired = 2;
  static constexpr float kThreshold = 0.85f;

  bool update(bool frame_valid, float deer_score) {
    if (!frame_valid) {
      reset();
      return false;
    }

    history_ = ((history_ << 1) | (deer_score >= kThreshold ? 1u : 0u)) & 0x7u;
    uint8_t hits = 0;
    for (uint8_t i = 0; i < kWindow; ++i) {
      hits += (history_ >> i) & 1u;
    }
    return hits >= kRequired;
  }

  void reset() { history_ = 0; }

 private:
  uint8_t history_ = 0;
};
