#pragma once

#include <vector>

// Host-only detector seam: the frame supplies already decoded result records.
// Tests compile the production adapter and gate, without model or camera work.
struct HostDetection {
  int category;
  float score;
};

struct HostImage {
  std::vector<HostDetection> detections;
};

class ESPDetDetect {
 public:
  const std::vector<HostDetection>& run(HostImage& image) {
    return image.detections;
  }
};
