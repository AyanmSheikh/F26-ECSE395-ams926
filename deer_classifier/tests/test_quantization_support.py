"""Preprocessing geometry and detector conventions used for int8 candidate checks."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quantization_support import (Sample, assert_disjoint, decode_espdet,
                                  capture_proxy, espdl_letterbox, espdl_score_threshold,
                                  match_detections, resolve_capture_max_side, select_calibration)


def outputs():
    result = {}
    for stage, side in enumerate((28, 14, 7)):
        result[f"box{stage}"] = np.ones((1, 4, side, side), dtype=np.float32)
        result[f"score{stage}"] = np.full((1, 1, side, side), -100, dtype=np.float32)
    return result


class QuantizationSupportTests(unittest.TestCase):
    def test_letterbox_padding_and_floor_sampling(self):
        source = np.arange(3 * 2 * 3, dtype=np.uint8).reshape(3, 2, 3)
        actual, mapping = espdl_letterbox(source, 4)
        expected = np.full((4, 4, 3), 114, dtype=np.uint8)
        expected[:, 1:3] = source[[0, 0, 1, 2]]
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual((mapping["left"], mapping["top"]), (1, 0))

    def test_wide_scene_is_not_stretched_or_cropped(self):
        source = np.zeros((480, 640, 3), dtype=np.uint8)
        actual, mapping = espdl_letterbox(source)
        self.assertEqual(actual.shape, (224, 224, 3))
        self.assertTrue((actual[:28] == 114).all())
        self.assertTrue((actual[28:196] == 0).all())
        self.assertTrue((actual[196:] == 114).all())
        self.assertEqual(mapping["top"], 28)

    def test_capture_proxy_reduces_rgb_with_preserved_aspect(self):
        rgb = np.full((480, 640, 3), (10, 20, 30), dtype=np.uint8)
        proxy = capture_proxy(rgb, 320)
        self.assertEqual(proxy.shape, (240, 320, 3))
        self.assertTrue((proxy == [10, 20, 30]).all())
        portrait = capture_proxy(np.zeros((640, 320, 3), dtype=np.uint8), 320)
        self.assertEqual(portrait.shape, (320, 160, 3))

    def test_capture_proxy_leaves_small_and_legacy_images_unchanged(self):
        rgb = np.arange(6 * 8 * 3, dtype=np.uint8).reshape(6, 8, 3)
        np.testing.assert_array_equal(capture_proxy(rgb, 320), rgb)
        np.testing.assert_array_equal(capture_proxy(rgb, 0), rgb)

    def test_capture_setting_obeys_saved_calibration_metadata(self):
        self.assertEqual(resolve_capture_max_side(None), 320)
        self.assertEqual(resolve_capture_max_side(None, {"capture_max_side": 320}), 320)
        self.assertEqual(resolve_capture_max_side(None, {}), 0)  # Legacy exports.
        self.assertEqual(resolve_capture_max_side(0, {"capture_max_side": 0}), 0)
        with self.assertRaisesRegex(ValueError, "saved calibration"):
            resolve_capture_max_side(0, {"capture_max_side": 320})
        with self.assertRaisesRegex(ValueError, "saved calibration"):
            resolve_capture_max_side(320, {})

    def test_cli_rejects_native_capture_override_before_creating_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / "quantization_manifest.json").write_text(json.dumps({"settings": {"capture_max_side": 320}}))
            destination = folder / "must_not_exist"
            result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "quantize_and_evaluate.py"),
                                     "--native-graph", str(folder / "candidate.native"),
                                     "--dataset", str(folder / "unused_dataset"), "--output-dir", str(destination),
                                     "--capture-max-side", "0"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("saved calibration", result.stderr)
            self.assertFalse(destination.exists())

    def test_decode_named_heads_and_suppress_overlapping_boxes(self):
        raw = outputs()
        raw["score0"][0, 0, 10, 10] = 2
        raw["score1"][0, 0, 5, 5] = 1
        # Both decoded boxes are exactly [76,76,92,92] on the square input.
        raw["box1"][0, :, 5, 5] = (0.75, 0.75, 0.25, 0.25)
        _, mapping = espdl_letterbox(np.zeros((224, 224, 3), dtype=np.uint8))
        decoded = decode_espdet(raw, mapping)
        self.assertEqual(len(decoded), 1)
        np.testing.assert_array_equal(decoded[0, :4], [76, 76, 92, 92])
        self.assertAlmostEqual(decoded[0, 4], 0.8807970779)

    def test_empty_predictions_and_nonfinite_outputs(self):
        raw = outputs()
        _, mapping = espdl_letterbox(np.zeros((224, 224, 3), dtype=np.uint8))
        self.assertEqual(decode_espdet(raw, mapping).shape, (0, 5))
        raw["box2"][0, 0, 0, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            decode_espdet(raw, mapping)

    def test_quantized_logit_cutoff_matches_s3_postprocessor(self):
        cutoff = espdl_score_threshold(0.25)
        self.assertEqual(cutoff["integer_threshold"], -9)
        self.assertEqual(cutoff["logit_threshold"], -2.25)
        self.assertLess(cutoff["effective_probability_floor"], 0.10)
        raw = outputs()
        raw["score0"][0, 0, 10, 10] = -2.25
        _, mapping = espdl_letterbox(np.zeros((224, 224, 3), dtype=np.uint8))
        thresholds = {f"score{stage}": cutoff for stage in range(3)}
        self.assertEqual(len(decode_espdet(raw, mapping)), 0)
        actual = decode_espdet(raw, mapping, quantized_score_thresholds=thresholds)
        self.assertEqual(len(actual), 1)
        self.assertLess(actual[0, 4], 0.10)

    def test_matching_counts_one_box_once(self):
        predictions = np.array([[25, 25, 75, 75, 0.9], [25, 25, 75, 75, 0.8]])
        correct = match_detections(predictions, ((0.5, 0.5, 0.5, 0.5),), {"width": 100, "height": 100})
        self.assertTrue(correct[0].all())
        self.assertFalse(correct[1].any())

    def test_balanced_selection_is_seeded_and_content_overlap_fails(self):
        samples = [Sample(Path(str(i)), Path(str(i)), ((0.5, 0.5, 0.2, 0.2),) if i % 2 else (), str(i), "label")
                   for i in range(12)]
        first = select_calibration(samples, 8, 395)
        self.assertEqual(first, select_calibration(samples, 8, 395))
        self.assertEqual(sum(sample.positive for sample in first), 4)
        with self.assertRaisesRegex(ValueError, "overlap"):
            assert_disjoint(samples, [samples[0]])


if __name__ == "__main__":
    unittest.main()
