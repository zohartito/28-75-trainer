#!/usr/bin/env python3
"""Weekly practice-shot scoring loop for 28-75 Trainer.

Scans a practice root for shoot folders, scores each NEW or CHANGED shoot with
the existing trainer2875 scoring engine (the deterministic boundary lives in
`trainer2875.scoring` — this script only orchestrates), and appends the result
to a durable progress log.

Idempotent: a per-shoot content signature is cached in a ledger, so re-running
only scores folders that changed. Hard caps bound each run. `--dry-run` reports
what would be scored without writing anything.

Run:
    python3 scripts/weekly_progress.py --root ~/Pictures/28-75-practice
    python3 scripts/weekly_progress.py --dry-run

Structured run summary (JSON matching scripts/weekly-progress.schema.json) is
printed to stdout for downstream tooling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trainer2875.analysis import analyze_folder
from trainer2875.coaching import build_coaching_report
from trainer2875.mission import mission_for_focus
from trainer2875.models import SUPPORTED_IMAGE_EXTENSIONS

SCHEMA_VERSION = "1.0"
DEFAULT_PRACTICE_ROOT = "~/Pictures/28-75-practice"
STATE_DIR = REPO_ROOT / "state"
LEDGER_PATH = STATE_DIR / "progress-ledger.json"
LOG_PATH = STATE_DIR / "progress-log.jsonl"
PROGRESS_MD = STATE_DIR / "PROGRESS.md"
LEARNINGS_PATH = REPO_ROOT / ".claude" / "LEARNINGS.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def infer_focus(folder_name: str) -> str | None:
    name = folder_name.lower()
    if re.search(r"(?<![a-z0-9])75mm(?![a-z0-9])", name) or "tele" in name or "compression" in name:
        return "tele"
    if re.search(r"(?<![a-z0-9])28mm(?![a-z0-9])", name) or "wide" in name:
        return "wide"
    return None


def find_shoot_folders(root: Path) -> list[Path]:
    """A shoot = an immediate subfolder of `root` that holds >=1 supported image."""
    shoots: list[Path] = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        if any(
            f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
            for f in child.rglob("*")
        ):
            shoots.append(child)
    return shoots


def shoot_signature(folder: Path) -> str:
    """Signature over images and XMP sidecars (path, size, mtime)."""
    parts: list[str] = []
    for f in sorted(folder.rglob("*")):
        if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS | {".xmp"}:
            stat = f.stat()
            parts.append(f"{f.relative_to(folder)}|{stat.st_size}|{stat.st_mtime_ns}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest


def load_ledger() -> dict:
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    return {"schema_version": SCHEMA_VERSION, "shoots": {}, "runs": []}


def score_shoot(folder: Path) -> dict:
    focus = infer_focus(folder.name)
    mission = mission_for_focus(focus)
    analysis = analyze_folder(str(folder))
    report = build_coaching_report(analysis, mission)
    card = report.scorecard
    return {
        "schema_version": SCHEMA_VERSION,
        "ts": _now(),
        "shoot": folder.name,
        "shoot_path": str(folder),
        "mission_id": mission.mission_id,
        "focus": focus,
        "photo_count": len(analysis.photos),
        "total_score": card.total_score,
        "component_scores": card.component_scores,
        "missing_focal_lengths": list(card.missing_focal_lengths),
        "next_mission_id": report.next_mission.mission_id,
    }


def append_progress_md(entries: list[dict]) -> None:
    header = "# 28-75 Trainer — Progress Log\n\n| date | shoot | mission | photos | score | weakest | next mission |\n|------|-------|---------|--------|-------|---------|--------------|\n"
    if not PROGRESS_MD.exists():
        PROGRESS_MD.write_text(header, encoding="utf-8")
    rows = []
    for e in entries:
        weakest = min(e["component_scores"], key=e["component_scores"].get) if e["component_scores"] else "-"
        rows.append(
            f"| {e['ts'][:10]} | {e['shoot']} | {e['mission_id']} | "
            f"{e['photo_count']} | {e['total_score']} | {weakest} | {e['next_mission_id']} |\n"
        )
    with PROGRESS_MD.open("a", encoding="utf-8") as fh:
        fh.writelines(rows)


def append_log(entries: list[dict]) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, sort_keys=True) + "\n")


def append_learning(summary: dict) -> None:
    if not LEARNINGS_PATH.exists():
        return
    scored = summary["scored"]
    if not scored:
        line = f"- {summary['generated_at'][:10]} weekly-progress: no new shoots found under {summary['practice_root']}.\n"
    else:
        delta = summary["delta"]
        arrow = "flat" if delta == 0 else ("up" if delta > 0 else "down")
        weak = summary.get("run_weakest_component", "-")
        line = (
            f"- {summary['generated_at'][:10]} weekly-progress: scored {len(scored)} shoot(s), "
            f"mean {summary['run_mean_score']} ({arrow} {delta:+} vs prev). "
            f"Fleet-weakest component: {weak}. Idempotent ledger skipped {summary['skipped_count']}.\n"
        )
    with LEARNINGS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line)


def build_summary(scored: list[dict], skipped: int, root: Path, ledger: dict, dry_run: bool) -> dict:
    scores = [e["total_score"] for e in scored]
    run_mean = round(sum(scores) / len(scores)) if scores else None
    prev_runs = ledger.get("runs", [])
    prev_mean = prev_runs[-1]["run_mean_score"] if prev_runs else run_mean
    # Aggregate weakest component across this run's shoots.
    agg: dict[str, list[int]] = {}
    for e in scored:
        for name, val in e["component_scores"].items():
            agg.setdefault(name, []).append(val)
    run_weakest = min(agg, key=lambda k: sum(agg[k]) / len(agg[k])) if agg else "-"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "practice_root": str(root),
        "dry_run": dry_run,
        "new_count": len(scored),
        "skipped_count": skipped,
        "run_mean_score": run_mean,
        "prev_run_mean_score": prev_mean,
        "delta": run_mean - prev_mean if run_mean is not None and prev_mean is not None else None,
        "run_weakest_component": run_weakest,
        "scored": scored,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Weekly practice-shot scoring loop for 28-75 Trainer.")
    parser.add_argument(
        "--root",
        default=os.environ.get("TRAINER2875_PRACTICE_ROOT", DEFAULT_PRACTICE_ROOT),
        help="Practice root holding dated shoot subfolders.",
    )
    parser.add_argument("--max-shoots", type=int, default=20, help="Hard cap on shoots scored per run.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be scored; write nothing.")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser()
    ledger = load_ledger()

    if not root.exists() or not root.is_dir():
        summary = build_summary([], 0, root, ledger, args.dry_run)
        summary["note"] = "practice root missing — nothing to score"
        print(json.dumps(summary, indent=2))
        return 0

    shoots = find_shoot_folders(root)
    to_score: list[Path] = []
    skipped = 0
    for folder in shoots:
        sig = shoot_signature(folder)
        prev = ledger["shoots"].get(str(folder))
        if prev and prev.get("signature") == sig:
            skipped += 1
            continue
        to_score.append(folder)
    capped = to_score[: args.max_shoots]

    scored: list[dict] = []
    for folder in capped:
        entry = score_shoot(folder)
        entry["signature"] = shoot_signature(folder)
        scored.append(entry)

    summary = build_summary(
        [{k: v for k, v in e.items() if k != "signature"} for e in scored],
        skipped, root, ledger, args.dry_run,
    )

    if not args.dry_run and scored:
        STATE_DIR.mkdir(exist_ok=True)
        append_log([{k: v for k, v in e.items() if k != "signature"} for e in scored])
        append_progress_md(scored)
        for e in scored:
            ledger["shoots"][e["shoot_path"]] = {"signature": e["signature"], "ts": e["ts"]}
        ledger["runs"].append(
            {"ts": summary["generated_at"], "run_mean_score": summary["run_mean_score"], "new_count": summary["new_count"]}
        )
        ledger["runs"] = ledger["runs"][-52:]  # keep ~1 year of weekly runs
        LEDGER_PATH.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")

    if not args.dry_run:
        append_learning(summary)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
