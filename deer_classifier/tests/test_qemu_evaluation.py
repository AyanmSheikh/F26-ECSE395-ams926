"""Audit actual model/input identity and complete coverage before reporting accuracy."""

import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate_espdl_qemu import MAGIC, load_validated_run_metadata, main, parse_results, prepare_frames


def fixture():
    manifest = {
        "protocol": "DEERDS01", "model": {"sha256": "a" * 64, "size_bytes": 499712},
        "image_count": 2, "dataset": "held-out", "split": "val", "selection": "all available validation images",
        "preprocessing": {}, "images": [
            {"id": 0, "image": "deer.jpg", "has_deer": True, "rgb_sha256": "b" * 64},
            {"id": 1, "image": "empty.jpg", "has_deer": False, "rgb_sha256": "c" * 64},
        ],
    }
    log = ("ESP-ROM:esp32s3-20210327\n"
           f"BOOT dataset_eval model_bytes=499712 sha256={'a' * 64}\n"
           "MODEL_SELFTEST SKIP\n"
           f"RESULT id=0 score=0.90000000 rgb_sha256={'b' * 64} infer_ms=123\n"
           f"RESULT id=1 score=0.20000000 rgb_sha256={'c' * 64} infer_ms=123\n"
           "END count=2\n")
    return manifest, log


class QuantizedEvaluationTests(unittest.TestCase):
    def test_cli_blocks_missing_failed_or_unsuccessful_numerical_validation_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, metadata = root / "accuracy.json", root / "run.json"
            argv = ["evaluate_espdl_qemu.py", "--results", str(root / "not-read.log"),
                    "--manifest", str(root / "not-read.json"), "--output", str(output)]
            for settings in (None, {}, {"numeric_oracle_passed": False, "qemu_exit_code": 0},
                             {"numeric_oracle_passed": 1, "qemu_exit_code": 0},
                             {"numeric_oracle_passed": True, "qemu_exit_code": 1}):
                extra = []
                if settings is not None:
                    metadata.write_text(json.dumps(settings), encoding="utf-8")
                    extra = ["--run-metadata", str(metadata)]
                with self.subTest(settings=settings), patch.object(sys, "argv", argv + extra), \
                        patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code, 2)
                self.assertFalse(output.exists())

    def test_oracle_evidence_must_hash_match_and_contain_a_clean_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence, metadata = root / "oracle.log", root / "run.json"
            evidence.write_text("MODEL_SELFTEST PASS\n", encoding="utf-8")
            settings = {"numeric_oracle_passed": True, "qemu_exit_code": 0,
                        "oracle_log": {"path": "oracle.log", "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}}
            metadata.write_text(json.dumps(settings), encoding="utf-8")
            self.assertEqual(load_validated_run_metadata(metadata), settings)
            evidence.write_text("MODEL_SELFTEST FAIL\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_validated_run_metadata(metadata)
            settings["oracle_log"]["sha256"] = hashlib.sha256(evidence.read_bytes()).hexdigest()
            metadata.write_text(json.dumps(settings), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "MODEL_SELFTEST PASS"):
                load_validated_run_metadata(metadata)

    def test_complete_identity_checked_run_reports_threshold_accuracy(self):
        manifest, log = fixture()
        report = parse_results(log, manifest, [0.85, 0.1])
        self.assertEqual(report["image_count"], 2)
        self.assertEqual(report["image_presence"][0]["accuracy"], 1)
        self.assertEqual(report["image_presence"][0]["balanced_accuracy"], 1)
        self.assertEqual(report["image_presence"][1]["false_positive"], 1)

    def test_missing_duplicate_unknown_results_and_missing_end_fail(self):
        manifest, log = fixture()
        result0 = next(line for line in log.splitlines() if line.startswith("RESULT id=0"))
        variants = [log.replace(result0 + "\n", ""),
                    log.replace(result0, result0 + "\n" + result0),
                    log.replace("RESULT id=1", "RESULT id=7"),
                    log.replace("END count=2\n", "")]
        for variant in variants:
            with self.subTest(log=variant), self.assertRaises(ValueError):
                parse_results(variant, manifest)

    def test_model_or_rgb_identity_mismatch_fails(self):
        manifest, log = fixture()
        for variant in (log.replace("a" * 64, "d" * 64), log.replace("b" * 64, "d" * 64),
                        log.replace("model_bytes=499712", "model_bytes=123")):
            with self.subTest(log=variant), self.assertRaises(ValueError):
                parse_results(variant, manifest)

    def test_errors_reboots_and_invalid_scores_invalidate_completed_run(self):
        manifest, log = fixture()
        for bad in ("ERROR reason=inference", "Guru Meditation Error", "assert failed: conv", "ESP-ROM: reset"):
            with self.subTest(error=bad), self.assertRaises(ValueError):
                parse_results(log + bad + "\n", manifest)
        for score in ("nan", "inf", "-0.1", "1.1"):
            with self.subTest(score=score), self.assertRaises(ValueError):
                parse_results(log.replace("0.90000000", score), manifest)

    def test_candidate_score_floor_is_enforced(self):
        manifest, log = fixture()
        with self.assertRaises(ValueError):
            parse_results(log, manifest, [0.05])
        broken = copy.deepcopy(manifest)
        broken["images"][1]["id"] = 0
        with self.assertRaises(ValueError):
            parse_results(log, broken)

    def test_preparation_preserves_aspect_ratio_rgb_and_explicit_truth(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images, labels = root / "dataset/images/val", root / "dataset/labels/val"
            images.mkdir(parents=True)
            labels.mkdir(parents=True)
            Image.new("RGB", (400, 200), (255, 0, 0)).save(images / "deer.png")
            (labels / "deer.txt").write_text("0 0.5 0.5 0.2 0.3\n")
            model = root / "model.espdl"
            model.write_bytes(b"synthetic identity fixture")
            manifest = prepare_frames(root / "dataset", root / "prepared", model)
            binary = (root / "prepared/frames.bin").read_bytes()
            self.assertEqual(binary[:8], MAGIC)
            self.assertEqual(struct.unpack_from("<IIII", binary, 8), (1, 0, 320, 160))
            rgb = binary[24:]
            self.assertEqual(len(rgb), 320 * 160 * 3)
            self.assertEqual(rgb, bytes((255, 0, 0)) * (320 * 160))
            self.assertEqual(manifest["images"][0]["rgb_sha256"], hashlib.sha256(rgb).hexdigest())
            self.assertTrue(manifest["images"][0]["has_deer"])
            with self.assertRaises(FileExistsError):
                prepare_frames(root / "dataset", root / "prepared", model)
            (labels / "deer.txt").unlink()
            with self.assertRaises(FileNotFoundError):
                prepare_frames(root / "dataset", root / "missing-label", model)


if __name__ == "__main__":
    unittest.main()
