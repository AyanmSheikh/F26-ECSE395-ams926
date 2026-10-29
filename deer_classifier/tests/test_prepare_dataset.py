from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


class DatasetTests(unittest.TestCase):
    def test_documented_relative_archive_path(self):
        script = Path(__file__).resolve().parents[1] / "prepare_dataset.py"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "datasets" / "source"
            source.mkdir(parents=True)
            with zipfile.ZipFile(source / "deer.zip", "w") as archive:
                for split in ("train", "valid"):
                    name = f"camera_{split}_im_1"
                    archive.writestr(f"Lila.v1.3k/{split}/images/{name}.jpg", b"placeholder")
                    archive.writestr(f"Lila.v1.3k/{split}/labels/{name}.txt", "0 0.5 0.5 0.2 0.2\n")
            result = subprocess.run([sys.executable, str(script), "datasets/source/deer.zip"],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list((root / "datasets/deer/images").rglob("*.jpg"))), 2)


if __name__ == "__main__":
    unittest.main()
