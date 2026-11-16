from __future__ import annotations

import json
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class WeeklyPlistTests(unittest.TestCase):
    def test_generated_schedule_uses_selected_clone_and_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clone = root / "selected clone"
            (clone / "scripts").mkdir(parents=True)
            shutil.copyfile(REPO_ROOT / "scripts/weekly_progress.py", clone / "scripts/weekly_progress.py")
            shutil.copytree(REPO_ROOT / "trainer2875", clone / "trainer2875", ignore=shutil.ignore_patterns("__pycache__"))
            output = root / "agents" / "weekly.plist"
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts/generate_weekly_plist.py"), str(output),
                 "--repo", str(clone), "--python", sys.executable],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = plistlib.loads(output.read_bytes())
            self.assertEqual(config["ProgramArguments"], [sys.executable, str(clone / "scripts/weekly_progress.py")])
            self.assertEqual(config["WorkingDirectory"], str(clone))
            self.assertEqual(config["StartCalendarInterval"], {"Weekday": 1, "Hour": 8, "Minute": 15})
            self.assertFalse(config["RunAtLoad"])
            for key in ("StandardOutPath", "StandardErrorPath"):
                self.assertEqual(config[key], str(clone / "state/weekly-launchd.log"))
                self.assertTrue(Path(config[key]).parent.is_dir())
            smoke = subprocess.run(
                [*config["ProgramArguments"], "--root", str(root / "missing-practice"), "--dry-run"],
                cwd=config["WorkingDirectory"], capture_output=True, text=True, check=False,
            )
            self.assertEqual(smoke.returncode, 0, smoke.stderr)
            self.assertEqual(json.loads(smoke.stdout)["new_count"], 0)
