"""Host contract checks for the production C++ detector-to-gate adapter.

The detector seam supplies result records; it does not run inference or model
preprocessing. The actual adapter and temporal gate are compiled unchanged.
"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeerPresenceAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # CXX names one compiler executable. Keep paths (including Windows
        # backslashes and spaces) intact rather than parsing shell arguments.
        compiler_override = os.environ.get("CXX")
        if compiler_override:
            compiler = [compiler_override]
        else:
            compiler_path = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
            if compiler_path is None:
                raise RuntimeError("Host Clang/GCC-style C++17 compiler required; set CXX to its executable")
            compiler = [compiler_path]
        cls.temporary = tempfile.TemporaryDirectory(prefix="deer-adapter-test-")
        cls.addClassCleanup(cls.temporary.cleanup)
        executable_name = "deer_presence_contract.exe" if os.name == "nt" else "deer_presence_contract"
        cls.executable = Path(cls.temporary.name) / executable_name
        command = [
            *compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-I", str(ROOT / "tests/cpp/stubs"),
            "-I", str(ROOT),
            str(ROOT / "tests/cpp/deer_presence_contract.cpp"),
            "-o", str(cls.executable),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(f"Adapter test compilation failed:\n{result.stdout}{result.stderr}")

    def check_contract(self, scenario):
        result = subprocess.run([str(self.executable), scenario], capture_output=True,
                                text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_deer_scores_clear_confirmed_history(self):
        self.check_contract("invalid_deer")

    def test_invalid_score_cannot_hide_beside_a_valid_deer(self):
        self.check_contract("invalid_mixed")

    def test_invalid_non_deer_score_invalidates_the_frame(self):
        self.check_contract("invalid_non_deer")

    def test_valid_results_select_only_the_maximum_deer_score(self):
        self.check_contract("valid_maximum")

    def test_empty_non_deer_and_zero_scores_are_valid_misses(self):
        self.check_contract("valid_zero")

    def test_threshold_and_explicit_reset_contract(self):
        self.check_contract("reset")


if __name__ == "__main__":
    unittest.main()
