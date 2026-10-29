"""Metrics failure modes that could disguise a weak detector as a good one."""

import json
import logging
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_checkpoint import NmsTimeoutWatcher
from image_metrics import read_deer_label, summarize_presence


class PresenceMetricsTests(unittest.TestCase):
    def test_threshold_is_inclusive_and_confusion_counts_are_correct(self):
        rows = [
            {"image": "deer-hit", "has_deer": True, "score": 0.85},
            {"image": "deer-miss", "has_deer": True, "score": 0.2},
            {"image": "false-alarm", "has_deer": False, "score": 0.9},
            {"image": "empty", "has_deer": False, "score": 0.0},
        ]
        result = summarize_presence(rows, [0.85])[0]
        for name in ("true_positive", "false_negative", "false_positive", "true_negative"):
            self.assertEqual(result[name], 1)
        for name in ("precision", "recall", "false_positive_rate", "missed_deer_rate", "accuracy", "specificity", "balanced_accuracy"):
            self.assertEqual(result[name], 0.5)

    def test_no_predictions_and_no_negatives_do_not_invent_success_rates(self):
        result = summarize_presence([{"image": "deer", "has_deer": True, "score": 0}], [0.85])[0]
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["false_positive_rate"])
        self.assertIsNone(result["balanced_accuracy"])
        self.assertEqual(result["missed_deer_rate"], 1)
        json.dumps(result, allow_nan=False)

    def test_duplicates_empty_evaluation_and_invalid_scores_are_rejected(self):
        row = {"image": "same", "has_deer": False, "score": 0}
        for rows in ([], [row, row], [{**row, "score": float("nan")}], [{**row, "score": 2}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                summarize_presence(rows, [0.85])

    def test_missing_label_cannot_be_silently_counted_as_a_negative(self):
        with tempfile.TemporaryDirectory() as folder:
            label = Path(folder) / "label.txt"
            with self.assertRaises(FileNotFoundError):
                read_deer_label(label)
            label.write_text("")
            self.assertFalse(read_deer_label(label))
            label.write_text("0 0.5 0.4 0.3 0.2\n")
            self.assertTrue(read_deer_label(label))

    def test_wrong_classes_and_invalid_boxes_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            label = Path(folder) / "label.txt"
            for line in ("1 0.5 0.5 0.3 0.2", "0 nan 0.5 0.3 0.2", "0 0.5 0.5 0 0.2", "0 0.5"):
                label.write_text(line)
                with self.subTest(line=line), self.assertRaises(ValueError):
                    read_deer_label(label)

    def test_nms_timeout_warnings_are_detected_even_with_ansi_or_prefixes(self):
        watcher = NmsTimeoutWatcher()
        watcher.emit(logging.LogRecord("ultralytics", logging.WARNING, "", 0,
                                       "WARNING NMS time limit %.3fs exceeded", (15.0,), None))
        self.assertEqual(watcher.messages, ["WARNING NMS time limit 15.000s exceeded"])
        watcher.emit(logging.LogRecord("ultralytics", logging.INFO, "", 0, "normal evaluation", (), None))
        self.assertEqual(len(watcher.messages), 1)


if __name__ == "__main__":
    unittest.main()
