from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "weekly_progress.py"


def _run(root: Path, *extra: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *extra],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_missing_root_reports_empty(tmp_path):
    summary = _run(tmp_path / "does-not-exist", "--dry-run")
    assert summary["new_count"] == 0
    assert summary["scored"] == []


def test_dry_run_scores_shoot_but_writes_nothing(tmp_path):
    shoot = tmp_path / "2026-W32_28mm-walk"
    shoot.mkdir()
    (shoot / "frame_28mm.jpg").write_bytes(b"not-a-real-jpeg")

    summary = _run(tmp_path, "--dry-run")
    assert summary["dry_run"] is True
    assert summary["new_count"] == 1
    assert summary["scored"][0]["shoot"] == "2026-W32_28mm-walk"
    assert "total_score" in summary["scored"][0]
