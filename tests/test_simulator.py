from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_simulator.py"


class SimulatorDestinationTests(unittest.TestCase):
    def test_empty_destination_and_explicit_keep_run_successfully(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for options in ([], ["--keep"]):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), str(output), *options],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((output / "summary.json").is_file())
                marker = output / "MARKER.txt"
                if options:
                    self.assertEqual(marker.read_text(encoding="utf-8"), "keep me")
                marker.write_text("keep me", encoding="utf-8")

    def test_nonempty_destination_is_refused_without_deleting_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "existing"
            (output / "sub").mkdir(parents=True)
            marker = output / "MARKER.txt"
            nested = output / "sub" / "other.txt"
            marker.write_text("keep me", encoding="utf-8")
            nested.write_text("also keep me", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(output)],
                capture_output=True, text=True, check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("nonempty", result.stderr)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep me")
            self.assertEqual(nested.read_text(encoding="utf-8"), "also keep me")
