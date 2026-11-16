from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

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


def test_no_observations_has_no_mean_or_delta(tmp_path):
    ledger = {"runs": [{"run_mean_score": 48, "new_count": 1}]}
    summary = weekly_progress.build_summary([], 1, tmp_path, ledger, False)
    assert summary["new_count"] == 0
    assert summary["run_mean_score"] is None
    assert summary["prev_run_mean_score"] == 48
    assert summary["delta"] is None
    empty = weekly_progress.build_summary([], 0, tmp_path, {}, True)
    assert empty["run_mean_score"] is None
    assert empty["prev_run_mean_score"] is None
    assert empty["delta"] is None
    scored = [{"total_score": 50, "component_scores": {"volume": 50}}]
    observed = weekly_progress.build_summary(scored, 0, tmp_path, ledger, False)
    assert observed["run_mean_score"] == 50
    assert observed["delta"] == 2


def test_dates_do_not_select_a_focal_mission(tmp_path):
    for name in ("2026-11-14_walk", "2026-11-28_walk", "2028-01-01_walk", "frame_175_walk"):
        assert weekly_progress.infer_focus(name) is None
    for name, focus in (("2026-W32_28mm-walk", "wide"), ("walk-75mm", "tele"), ("wide", "wide"), ("tele", "tele"), ("compression", "tele")):
        assert weekly_progress.infer_focus(name) == focus
    entries = []
    for name in ("2026-11-14_walk", "2026-11-28_walk"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "frame_28mm.jpg").write_bytes(b"same photo")
        entries.append(weekly_progress.score_shoot(folder))
    assert entries[0]["mission_id"] == entries[1]["mission_id"]
    assert entries[0]["total_score"] == entries[1]["total_score"]


def isolate_outputs(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setattr(weekly_progress, "STATE_DIR", state)
    for attribute, name in (("LEDGER_PATH", "ledger.json"), ("LOG_PATH", "log.jsonl"), ("PROGRESS_MD", "PROGRESS.md"), ("LEARNINGS_PATH", "LEARNINGS.md")):
        monkeypatch.setattr(weekly_progress, attribute, state / name)
    return state


@pytest.mark.parametrize("attribute", ["LEDGER_PATH", "LOG_PATH", "PROGRESS_MD", "LEARNINGS_PATH"])
def test_weekly_outputs_refuse_symlinks(tmp_path, monkeypatch, attribute):
    isolate_outputs(tmp_path, monkeypatch)
    root = tmp_path / "practice"
    shoot = root / "walk"
    shoot.mkdir(parents=True)
    (shoot / "frame.jpg").write_bytes(b"photo")
    outside = tmp_path / "outside.txt"
    original = '{"schema_version":"1.0","shoots":{},"runs":[]}'
    outside.write_text(original)
    getattr(weekly_progress, attribute).symlink_to(outside)

    with pytest.raises((ValueError, OSError)):
        weekly_progress.main(["--root", str(root)])
    assert outside.read_text() == original


def test_weekly_markdown_escapes_imported_names(tmp_path, monkeypatch, capsys):
    isolate_outputs(tmp_path, monkeypatch)
    root = tmp_path / "<script> | [root](x)"
    shoot = root / "<img src=x onerror=alert(1)> | pipe\n# injected"
    shoot.mkdir(parents=True)
    (shoot / "frame.jpg").write_bytes(b"photo")
    weekly_progress.LEARNINGS_PATH.write_text("# Learnings\n")
    assert weekly_progress.main(["--root", str(root)]) == 0
    capsys.readouterr()
    markdown = weekly_progress.PROGRESS_MD.read_text()
    assert "<img" not in markdown
    assert "&lt;img" in markdown
    assert "\\| pipe" in markdown
    assert "\n# injected" not in markdown
    assert weekly_progress.main(["--root", str(root)]) == 0
    learning = weekly_progress.LEARNINGS_PATH.read_text()
    assert "<script>" not in learning
    assert "[root](x)" not in learning
