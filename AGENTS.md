# 28-75-trainer — Claude Code project memory

## What this is
28-75 Trainer is a local deliberate-practice tool for photographers using a 28-75mm zoom. It gives a mission, reviews a folder of images without modifying originals, writes coaching reports, and recom

## How to verify a change
- Tests: `pytest -q`
- Lint:  `(none detected)`

## Self-improving loop (close the loop)
Run an agent until it verifies its own output, then commit:
```
python3 ~/.agent-kit/verify_loop.py --task "<what to do>" --verify "pytest -q" --cwd . --max-iters 5 --commit
```

## Layout
`.github/`, `docs/`, `scripts/`, `tests/`, `trainer2875/`

## Conventions
- Follow CONVENTIONS.md (if present) and the global ~/.claude/CLAUDE.md.
- Make surgical, single-purpose changes; match existing style.

## Lessons
Corrections, gotchas, and "don't do X again" notes accumulate in `.claude/lessons.md`
and are consolidated by the `dream` skill. Read them before non-trivial work.

## Agent rules (all harnesses)
- Determinism boundary: anything that must be EXACT (money, geometry, safety limits, scoring, pricing) lives in code; the model only orchestrates and judges.
- Keep this file current: when you change how this repo is run, tested, or structured, update AGENTS.md in the same commit. Keep it under ~150 lines.
