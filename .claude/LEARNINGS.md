# LEARNINGS — 28-75-trainer

Durable, machine-appended learnings from the loops in this repo. The
`weekly_progress.py` loop appends one bullet per run (counts, mean score, delta
vs previous run, fleet-weakest component). Read before non-trivial work; the
`dream` skill promotes recurring items into AGENTS.md.

## Loop: weekly practice-shot scoring (`scripts/weekly_progress.py`)
- Scoring lives in `trainer2875.scoring` (determinism boundary); the loop only
  orchestrates folder discovery, idempotent change-detection, and logging.
- Idempotency key = SHA-256 over each shoot's (relpath, size, mtime) tuples,
  cached in `state/progress-ledger.json`. Re-runs only score changed folders.

## Run log
- (loop appends dated bullets below this line)
