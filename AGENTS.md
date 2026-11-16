# 28-75-trainer — Claude Code project memory

## What this is
28-75 Trainer is a local deliberate-practice tool for photographers using a 28-75mm zoom. It gives a mission, reviews a folder of images without modifying originals, writes coaching reports, and recom

## How to verify a change
- Supported platform: macOS with Python 3.10+; Windows/Linux safe I/O is unsupported.
- Tests: install `requirements-test.txt`, then run `python -m pytest -q` from the repo root.
- Lint:  `(none detected)`
- Simulator: `python scripts/run_simulator.py <empty-folder>`; nonempty destinations
  are refused unless `--keep` explicitly reuses generated files without deleting the folder.

## Self-improving loop (close the loop)
Run an agent until it verifies its own output, then commit:
```
python3 ~/.agent-kit/verify_loop.py --task "<what to do>" --verify "python -m pytest -q" --cwd . --max-iters 5 --commit
```

## Loops (this repo)
- **SCHED weekly — practice-shot scoring** (`scripts/weekly_progress.py`): scans a
  practice root for shoot folders, scores each NEW/CHANGED shoot with
  `trainer2875.scoring`, appends `state/progress-log.jsonl` + `state/PROGRESS.md`,
  and prints a run summary (JSON, `scripts/weekly-progress.schema.json`). Idempotent
  via a per-shoot SHA-256 signature ledger over image and XMP path/size/mtime;
  hard cap `--max-shoots` (default 20);
  `--dry-run` writes nothing. Practice root = `$TRAINER2875_PRACTICE_ROOT` or
  `~/Pictures/28-75-practice`. Durable learnings append to `.claude/LEARNINGS.md`.
  With no new observations, run mean and delta are JSON null; the previous observed mean is retained.
  - Schedule (write-only plist, not loaded): `launchd/com.zohar.trainer2875-weekly.plist`.
    Load: `cp launchd/com.zohar.trainer2875-weekly.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.zohar.trainer2875-weekly.plist`
  - Verify: `python -m pytest -q tests/test_weekly_progress.py`

## Layout
`.github/`, `docs/`, `launchd/`, `scripts/`, `state/` (runtime, gitignored), `tests/`, `trainer2875/`

## Conventions
- Follow CONVENTIONS.md (if present) and the global ~/.claude/CLAUDE.md.
- Make surgical, single-purpose changes; match existing style.

## Lessons
Corrections, gotchas, and "don't do X again" notes accumulate in `.claude/lessons.md`
and are consolidated by the `dream` skill. Read them before non-trivial work.

## Agent rules (all harnesses)
- Determinism boundary: anything that must be EXACT (money, geometry, safety limits, scoring, pricing) lives in code; the model only orchestrates and judges.
- Keep this file current: when you change how this repo is run, tested, or structured, update AGENTS.md in the same commit. Keep it under ~150 lines.
