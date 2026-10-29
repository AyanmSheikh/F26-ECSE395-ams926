"""Regression checks for preserving the deployed model during training/export."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import export_embedded
import run_espdet_training
import train_embedded
from training_utils import deploy_model, select_device, validate_settings


class TrainingSafetyTests(unittest.TestCase):
    def test_device_selection_uses_available_backend(self):
        for cuda, mps, expected in ((True, True, "0"), (False, True, "mps"), (False, False, "cpu")):
            torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: cuda),
                                    backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: mps)))
            self.assertEqual(select_device("auto", torch), expected)
        self.assertEqual(select_device("cpu"), "cpu")

    def test_invalid_training_settings_fail_before_training(self):
        for size, rate in (((0, 224), .001), ((224, 225), .001), ((224, 224), float("nan"))):
            with self.assertRaises(ValueError):
                validate_settings(size, 10, 8, 8, 0, rate, .5)
        for options in ({"warmup_bias_lr": float("nan")}, {"warmup_bias_lr": -1},
                        {"mosaic": 1.1}, {"scale": -0.1}, {"scale": float("inf")},
                        {"close_mosaic": -1}, {"cache": "invalid"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                validate_settings((224, 224), 10, 8, 8, 0, .0005, 3, **options)

    def test_empty_and_existing_exports_preserve_deployed_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deployed, candidate = root / "deer.espdl", root / "candidate.espdl"
            deployed.write_bytes(b"previous valid model")
            candidate.write_bytes(b"")
            with self.assertRaises(ValueError):
                deploy_model(candidate, deployed, overwrite=True)
            candidate.write_bytes(b"new model")
            with self.assertRaises(FileExistsError):
                deploy_model(candidate, deployed)
            self.assertEqual(deployed.read_bytes(), b"previous valid model")
            record = deploy_model(candidate, deployed, overwrite=True)
            self.assertEqual(deployed.read_bytes(), b"new model")
            self.assertEqual(record["size_bytes"], 9)
            self.assertEqual(len(record["sha256"]), 64)

    def test_wrapper_forwards_run_settings_and_quotes_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "esp-detection"
            (repo / "deploy").mkdir(parents=True)
            (repo / "train.py").touch()
            (repo / "deploy/quantize.py").touch()
            dataset = root / "data # one"
            for sub in ("images/train", "images/val", "labels/train", "labels/val"):
                (dataset / sub).mkdir(parents=True)
            checkpoint = root / "best.pt"
            checkpoint.write_bytes(b"test checkpoint")
            argv = ["train_embedded.py", "--esp-detection", str(repo), "--dataset", str(dataset),
                    "--pretrained", str(checkpoint), "--output", str(root / "candidate.espdl"),
                    "--run-name", "candidate_1", "--workers", "0", "--patience", "12"]
            with patch.object(sys, "argv", argv), patch.object(train_embedded.subprocess, "run") as run:
                train_embedded.main()
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--device") + 1], "auto")
            self.assertEqual(command[command.index("--patience") + 1], "12")
            self.assertEqual(command[command.index("--warmup-bias-lr") + 1], "0.0")
            self.assertEqual(command[command.index("--warmup-epochs") + 1], "3.0")
            self.assertEqual(command[command.index("--mosaic") + 1], "0.2")
            self.assertEqual(command[command.index("--scale") + 1], "0.25")
            self.assertIn("--cos-lr", command)
            self.assertIn("--no-amp", command)
            config = (root / "candidate_1_dataset.yaml").read_text(encoding="utf-8")
            self.assertIn(f"path: {json.dumps(dataset.as_posix())}", config)

    def test_train_only_passes_safe_settings_and_preserves_existing_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, dataset, deployed = root / "source.pt", root / "data.yaml", root / "deer.espdl"
            checkpoint.write_bytes(b"source checkpoint")
            dataset.write_text("names: [deer]", encoding="utf-8")
            deployed.write_bytes(b"previous deployed model")
            captured = {}

            def train(**settings):
                captured.update(settings)
                run_dir = Path(settings["project"]) / settings["name"]
                (run_dir / "weights").mkdir(parents=True)
                (run_dir / "weights/best.pt").write_bytes(b"trained checkpoint")
                return SimpleNamespace(save_dir=run_dir)

            argv = ["run_espdet_training.py", "--esp-detection", str(root), "--pretrained_path", str(checkpoint),
                    "--dataset", str(dataset), "--size", "224", "224", "--espdl", str(deployed),
                    "--run-name", "safe_train", "--train-only", "--device", "cpu", "--cache", "ram"]
            with patch.object(sys, "argv", argv), patch.object(run_espdet_training, "load_esp_detection",
                    return_value=(train, unittest.mock.Mock(), unittest.mock.Mock())) as load:
                run_espdet_training.main()
                load.return_value[1].assert_not_called()
                load.return_value[2].assert_not_called()
            self.assertEqual(captured["warmup_bias_lr"], 0.0)
            self.assertEqual(captured["warmup_epochs"], 3.0)
            self.assertEqual(captured["mosaic"], .2)
            self.assertEqual(captured["scale"], .25)
            self.assertEqual(captured["cache"], "ram")
            self.assertTrue(captured["cos_lr"])
            self.assertFalse(captured["amp"])
            self.assertEqual(captured["close_mosaic"], 10)
            self.assertEqual(deployed.read_bytes(), b"previous deployed model")
            manifest = json.loads((root / "safe_train/deer_run.json").read_text())
            self.assertEqual(manifest["status"], "trained; export pending")
            self.assertEqual(len(manifest["selected_checkpoint_sha256"]), 64)

    def test_failed_quantization_does_not_replace_previous_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint, dataset, deployed = root / "source.pt", root / "data.yaml", root / "deer.espdl"
            checkpoint.write_bytes(b"source checkpoint")
            dataset.write_text("names: [deer]", encoding="utf-8")
            deployed.write_bytes(b"previous model")

            def train(**settings):
                run_dir = Path(settings["project"]) / settings["name"]
                (run_dir / "weights").mkdir(parents=True)
                (run_dir / "weights/best.pt").write_bytes(b"selected checkpoint")
                return SimpleNamespace(save_dir=run_dir)

            def broken_quantizer(**settings):
                Path(settings["espdl_model_path"]).write_bytes(b"partial corrupt export")
                raise RuntimeError("simulated export failure")

            argv = ["run_espdet_training.py", "--esp-detection", str(root), "--pretrained_path", str(checkpoint),
                    "--dataset", str(dataset), "--size", "224", "224", "--calib_data", str(root),
                    "--espdl", str(deployed), "--run-name", "attempt_1", "--overwrite-output", "--device", "cpu"]
            with patch.object(sys, "argv", argv), patch.object(run_espdet_training, "load_esp_detection",
                       return_value=(train, lambda *args: None, broken_quantizer)):
                with self.assertRaisesRegex(RuntimeError, "simulated"):
                    run_espdet_training.main()
            self.assertEqual(deployed.read_bytes(), b"previous model")
            self.assertTrue((root / "attempt_1/weights/best.pt").is_file())
            self.assertEqual(json.loads((root / "attempt_1/deer_run.json").read_text())["status"],
                             "trained; export pending")

    def test_reused_run_fails_before_loading_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "existing").mkdir()
            argv = ["export_embedded.py", "--esp-detection", str(root), "--checkpoint", str(root / "best.pt"),
                    "--calib-data", str(root), "--output", str(root / "deer.espdl"), "--run-name", "existing"]
            with patch.object(sys, "argv", argv), patch.object(export_embedded, "load_esp_detection") as load:
                with self.assertRaises(SystemExit) as failure:
                    export_embedded.main()
            self.assertEqual(failure.exception.code, 2)
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
