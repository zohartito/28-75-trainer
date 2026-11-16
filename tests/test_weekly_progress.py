from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import weekly_progress

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


def test_sidecar_change_rescores_shoot(tmp_path, monkeypatch, capsys):
    root = tmp_path / "practice"
    shoot = root / "walk"
    shoot.mkdir(parents=True)
    (shoot / "frame.ARW").write_bytes(b"raw placeholder")
    sidecar = shoot / "frame.XMP"
    sidecar.write_text('<x FocalLength="28/1" PixelXDimension="6000" PixelYDimension="4000"/>')
    state = tmp_path / "state"
    monkeypatch.setattr(weekly_progress, "STATE_DIR", state)
    monkeypatch.setattr(weekly_progress, "LEDGER_PATH", state / "ledger.json")
    monkeypatch.setattr(weekly_progress, "LOG_PATH", state / "log.jsonl")
    monkeypatch.setattr(weekly_progress, "PROGRESS_MD", state / "PROGRESS.md")
    monkeypatch.setattr(weekly_progress, "LEARNINGS_PATH", tmp_path / "absent.md")

    assert weekly_progress.main(["--root", str(root)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["scored"][0]["missing_focal_lengths"] == [35, 50, 75]
    sidecar.write_text('<x FocalLength="75/1" PixelXDimension="6000" PixelYDimension="4000"/>')
    assert weekly_progress.main(["--root", str(root)]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["new_count"] == 1
    assert second["scored"][0]["missing_focal_lengths"] == [28, 35, 50]
    assert weekly_progress.main(["--root", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["skipped_count"] == 1
