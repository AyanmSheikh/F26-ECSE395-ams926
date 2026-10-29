"""Turn per-frame deer detection confidence into a stable multi-frame trigger."""

from collections import deque


class TemporalDeerGate:
    """Assert deer when enough recent frames contain a confident deer box.

    Call ``update(None)`` after a camera/inference failure; it clears history so
    stale positives cannot trigger the downstream response.
    """

    def __init__(self, window: int = 3, required: int = 2, threshold: float = 0.85):
        if window < 1 or required < 1 or required > window:
            raise ValueError("require 1 <= required <= window")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")
        self.window = window
        self.required = required
        self.threshold = threshold
        self._detections: deque[bool] = deque(maxlen=window)

    def update(self, deer_confidence: float | None) -> bool:
        """Add one frame result and return whether the deer signal is asserted."""
        if deer_confidence is None:
            self._detections.clear()
            return False
        if not 0.0 <= deer_confidence <= 1.0:
            self._detections.clear()
            raise ValueError("deer_confidence must be in [0, 1]")
        self._detections.append(deer_confidence >= self.threshold)
        return sum(self._detections) >= self.required

    def reset(self) -> None:
        self._detections.clear()
