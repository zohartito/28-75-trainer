# Session Log - 2026-05-09

## Objective

Talk through the product idea, make the roadmap professional-grade, audit what has been done and what should happen next, decide whether GitHub should be updated, and log wins and failures.

## Work Completed

| Area | Result |
|---|---|
| Roadmap | Replaced the thin v0.1-v1.0 roadmap with a detailed v0.1-v2.0 product roadmap |
| Strategy | Added `docs/product-strategy-audit-2026-05-09.md` |
| Retrospective | Appended a 2026-05-09 entry with wins, failures, and operating rules |
| PR notes | Updated `docs/pr-description.md` to include roadmap/audit context |
| Hardening | Moved review output validation before scans; guarded report source/output same-path; refused symlink outputs; skipped symlinked image inputs |
| Truth audit | Added schema validation for loaded JSON reports, visible report evidence limits, and source-labeled report headings |
| Simulator | Added `scripts/run_simulator.py` with balanced, missing-metadata, exact-duplicate, unsupported-only, corrupt, and nested-uppercase cases |
| Tests | Expanded the suite from 9 to 24 tests; `python -m unittest discover -s tests` passed |
| Subagents | Launched independent roadmap, market, code-audit, QA, and UX agents |

## Product Direction

The product should own lens-specific deliberate practice. The winning loop is:

`mission -> real shoot -> local evidence -> coaching -> next mission -> measurable progress`

The next code should not jump straight to vague AI critique. The next code should make the evidence better: EXIF, contact sheets, versioned analysis schema, safer folder traversal, and session history.

## Wins To Preserve

| Win | Keep Doing |
|---|---|
| Build before broad audit | Audit real artifacts, not intentions |
| Local-first trust | Default to no network and no original mutation |
| Evidence-backed scoring | Show inputs for every derived score |
| Browser report verification | Keep checking generated reports in a real browser path |
| Reviewer pairing | A reviewer caught the partial-output bug before final commit |
| Simulator gate | Synthetic folders now catch regressions before real photo folders are available |

## Failures To Avoid

| Failure | Prevention |
|---|---|
| Docs drifting ahead of code | Every claim needs a command, test, or roadmap label |
| Subagent cap churn | Close finished agents before launching more |
| Audit-loop spiral | If process grows faster than product, ship the smallest useful next slice |
| Overconfident image signals | Blur/hash/AI claims need fixtures, thresholds, and conservative language |
| Placeholder fixture collisions | Simulator images must be unique unless the case is intentionally testing exact duplicates |
| PR without remote/permission | Prepare GitHub notes, but do not push without explicit approval |
| Filesystem trust gaps | Add regression tests for symlink and overwrite behavior before changing traversal again |

## GitHub Status

| Item | Status |
|---|---|
| Local branch | `codex/28-75-trainer-v0-1` |
| Last committed v0.1 | `6ffc7ce5913db4d8912e466962a85bdb31c6dca5` |
| Remote | None configured |
| Recommendation | Add a remote, push the branch, and open a draft PR after user approval |

## Open Questions

| Question | Why It Matters |
|---|---|
| What real photo folders can we test on? | v1.0 needs field validation |
| Should EXIF use Pillow first, ExifTool first, or both as optional adapters? | This determines dependency and packaging shape |
| Should contact sheets embed thumbnails or link to generated local assets? | This affects report size and privacy behavior |
| Should session history live in project folders or a user-level data directory? | This affects portability and privacy |

## Follow-Up From Subagent Audit

| Finding | Action |
|---|---|
| `review` output validation happened before writes but after folder analysis | Implemented: validation now happens before folder scanning |
| `report input.json --out input.json` could overwrite the source JSON | Implemented: source/output same-path validation now rejects it |
| Loaded report JSON has no schema validation before HTML rendering | Add a report schema/version gate before richer report reuse |
| User-facing wording sounded too certain for filename/dimension/hash evidence | Implemented: report now labels evidence source and states what v0.1 does not judge |
| Corrupt image files could still earn focal coverage from filename tags | Implemented: unreadable image headers warn and do not count toward focal coverage |
| Empty/unsupported-only folders could still look partially successful | Implemented: score is 0 and observations say there is not enough evidence |
| Simulator did not exist | Implemented: simulator now runs six regression scenarios and fails on expectation mismatches |
| Scratchpad in PR may be too internal | Decide whether `.codex-scratchpad/28-75-trainer/findings.md` belongs in public GitHub history before pushing |
