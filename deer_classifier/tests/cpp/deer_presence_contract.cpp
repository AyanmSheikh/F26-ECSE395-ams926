#include <cstdlib>
#include <initializer_list>
#include <iostream>
#include <limits>
#include <string>

#include "firmware/deer_presence.hpp"

namespace {
unsigned checks = 0;

void expect(bool actual, bool expected, const std::string& label) {
  ++checks;
  if (actual != expected) {
    std::cerr << label << ": expected " << expected << ", got " << actual << '\n';
    std::exit(1);
  }
}

bool frame(DeerPresenceSignal& signal,
           std::initializer_list<HostDetection> detections) {
  HostImage image{detections};
  return signal.update_frame(image);
}

void confirm(DeerPresenceSignal& signal, const std::string& label) {
  expect(frame(signal, {{0, 0.90f}}), false, label + " first hit");
  expect(frame(signal, {{0, 0.90f}}), true, label + " second hit");
}

void fresh_confirmation(DeerPresenceSignal& signal, const std::string& label) {
  expect(frame(signal, {{0, 0.91f}}), false, label + " first fresh hit");
  expect(frame(signal, {{0, 0.91f}}), true, label + " second fresh hit");
}

const float invalid_scores[] = {
    std::numeric_limits<float>::quiet_NaN(),
    std::numeric_limits<float>::infinity(),
    -std::numeric_limits<float>::infinity(),
    -0.1f,
    1.1f,
};

void invalid_deer_scores() {
  for (unsigned i = 0; i < sizeof(invalid_scores) / sizeof(invalid_scores[0]); ++i) {
    DeerPresenceSignal signal;
    const std::string label = "invalid deer score " + std::to_string(i);
    confirm(signal, label);
    expect(frame(signal, {{0, invalid_scores[i]}}), false, label + " invalid frame");
    fresh_confirmation(signal, label);
  }
}

void invalid_mixed_with_valid() {
  for (unsigned i = 0; i < sizeof(invalid_scores) / sizeof(invalid_scores[0]); ++i) {
    for (unsigned first = 0; first != 2; ++first) {
      DeerPresenceSignal signal;
      const std::string label = "mixed invalid score " + std::to_string(i) +
                                " first=" + std::to_string(first);
      confirm(signal, label);
      const bool actual = first
                              ? frame(signal, {{0, invalid_scores[i]}, {0, 1.0f}})
                              : frame(signal, {{0, 1.0f}, {0, invalid_scores[i]}});
      expect(actual, false, label + " invalid frame");
      fresh_confirmation(signal, label);
    }
  }
}

void invalid_non_deer_scores() {
  for (unsigned i = 0; i < sizeof(invalid_scores) / sizeof(invalid_scores[0]); ++i) {
    DeerPresenceSignal signal;
    const std::string label = "invalid non-deer score " + std::to_string(i);
    confirm(signal, label);
    expect(frame(signal, {{1, invalid_scores[i]}}), false, label + " invalid frame");
    fresh_confirmation(signal, label);
  }
}

void valid_category_and_maximum() {
  DeerPresenceSignal signal;
  expect(frame(signal, {{1, 1.0f}, {0, 0.2f}}), false, "other class cannot qualify");
  expect(frame(signal, {{0, 0.91f}, {0, 0.2f}}), false, "maximum deer score first hit");
  expect(frame(signal, {{0, 0.2f}, {1, 0.99f}, {0, 0.93f}}), true,
         "maximum deer score independent of result order");
}

void valid_zero_frames() {
  DeerPresenceSignal empty;
  confirm(empty, "empty result");
  expect(frame(empty, {}), true, "first empty frame is a valid miss");
  expect(frame(empty, {}), false, "second empty frame clears confirmation");

  DeerPresenceSignal other;
  confirm(other, "non-deer result");
  expect(frame(other, {{1, 1.0f}}), true, "valid other class is a miss");
  expect(frame(other, {{1, 0.0f}}), false, "second other-class miss clears confirmation");

  DeerPresenceSignal zero;
  confirm(zero, "zero score");
  expect(frame(zero, {{0, -0.0f}}), true, "signed zero is a valid miss");
  expect(frame(zero, {{0, 0.0f}}), false, "zero boundary remains valid");
}

void threshold_and_explicit_reset() {
  DeerPresenceSignal signal;
  expect(frame(signal, {{0, 0.85f}}), false, "threshold first hit");
  expect(frame(signal, {{0, 0.849f}}), false, "below threshold is a valid miss");
  expect(frame(signal, {{0, 0.85f}}), true, "two hits need not be consecutive");
  signal.reset();
  expect(frame(signal, {{0, 1.0f}}), false, "reset discards prior confirmation");
  expect(frame(signal, {{0, 1.0f}}), true, "one is a valid boundary score");
  expect(signal.invalidate_frame(), false, "camera or inference failure clears signal");
  fresh_confirmation(signal, "explicit invalidation");
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  const std::string test = argv[1];
  if (test == "invalid_deer") invalid_deer_scores();
  else if (test == "invalid_mixed") invalid_mixed_with_valid();
  else if (test == "invalid_non_deer") invalid_non_deer_scores();
  else if (test == "valid_maximum") valid_category_and_maximum();
  else if (test == "valid_zero") valid_zero_frames();
  else if (test == "reset") threshold_and_explicit_reset();
  else return 2;
  std::cout << test << ": " << checks << " checks passed\n";
  return 0;
}
