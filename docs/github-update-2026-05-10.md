# GitHub Update Packet - 2026-05-10

## Status

Published as a private GitHub repository:

- Repository: https://github.com/zohartito/28-75-trainer
- Initial import branch: `main`
- Import method: clean export of the tracked `28-75-trainer/` product folder only

The broad parent workspace should still not be pushed directly:

- Current branch: `codex/28-75-trainer-v0-1`
- Git remote: none configured
- Git root: `C:\Users\sample_user\Documents\Playground`
- Product path: `28-75-trainer/`
- Risk: the Git root contains many unrelated untracked workspace files, so pushing the parent repository as-is would be unsafe.

GitHub has been updated from a dedicated clean export. Do not push the broad `Playground` root.

## Recommended PR Title

Ship 28-75 Trainer v0.1 and competitive research roadmap

## Recommended PR Summary

This PR ships 28-75 Trainer as a local deliberate-practice CLI and documents the next roadmap based on competitive research.

The product loop is:

`mission -> review folder -> coaching report -> next mission`

The research update clarifies that 28-75 Trainer should not become a generic AI culling clone. Its strongest wedge is a local, evidence-labeled training loop that learns from serious review tools while owning lens-specific deliberate practice.

## What To Include

- v0.1 local training loop:
  - `trainer2875 mission`
  - `trainer2875 review <folder>`
  - `trainer2875 report <review.json>`
  - HTML and JSON coaching reports
  - sample shoot generator
  - simulator runner
- Trust hardening:
  - output preflight
  - symlink output refusal
  - symlinked image skip
  - report self-overwrite refusal
  - corrupt/empty/unsupported scoring fixes
  - schema validation for loaded reports
- Research and program docs:
  - `docs/roadmap.md`
  - `docs/research/competitive-learning-research-2026-05-10.md`
  - `docs/product-strategy-audit-2026-05-09.md`
  - `docs/pr-description.md`
  - `RETROSPECTIVE.md`

## Verification To Cite

- `python -B -m unittest discover -s tests` - 24 tests passed in the latest program-checkpoint verification.
- `python scripts/run_simulator.py reports/program-checkpoint-simulator` - six simulator scenarios passed:
  - balanced field map
  - missing metadata
  - exact duplicates
  - unsupported only
  - corrupt mixed folder
  - nested uppercase filenames

## Suggested GitHub Issues

| Issue | Scope | Acceptance Gate |
|---|---|---|
| [#1](https://github.com/zohartito/28-75-trainer/issues/1) v0.1.2 Field-Test Intelligence | More-than-12 grouping, role assignment, balanced picks, Lightroom fix notes | A 30-photo shoot produces 12 recommended picks, alternates, missing-vertical warnings, and Lightroom notes |
| [#2](https://github.com/zohartito/28-75-trainer/issues/2) RAW Metadata Intake | RAW focal length and basic metadata without mutating originals | RAW architectural-model shoot reports actual focal lengths and roles |
| [#3](https://github.com/zohartito/28-75-trainer/issues/3) Contact Sheet v1 | Local thumbnails and field-review evidence | Report has visual evidence without network assets or original mutation |
| [#4](https://github.com/zohartito/28-75-trainer/issues/4) Pre-v0.2 Hardening | Nested schema validation, atomic writes, metadata honesty | Richer reports fail safely |
| [#5](https://github.com/zohartito/28-75-trainer/issues/5) Practice System | First-week activation and session memory | Three reviewed sessions produce a history-backed next mission |

## Publish Checklist

1. Keep `zohartito/28-75-trainer` private unless the user requests public.
2. Push future updates from a clean product export or a dedicated local repo, not from `Playground`.
3. Use GitHub issues #1-#5 as the next execution queue.
4. Open a draft PR only after there is a stable feature-branch workflow.

## 2026-05-11 Update Queue

The next GitHub update should include the recommendation-bug fix and the newest roadmap execution work. The stale recommended set to document and ignore is:

`[1, 7, 11, 13, 14, 15, 17, 18, 19, 20, 21, 25]`

The fixed automated SD-card recommendation was:

`[7, 11, 15, 16, 18, 19, 21, 27, 30, 36, 39, 54]`

The visual-coach Adobe MCP handoff recommendation was:

`[7, 15, 16, 21, 23, 27, 30, 31, 36, 39, 43, 54]`

GitHub issue updates to make:

| Issue | Update |
|---|---|
| #1 Field-Test Intelligence | Note that stale-order recommendation was reproduced and source-level spread selection tests were added |
| #2 RAW Metadata Intake | Elevate because real SD-card workflow produced RAW/JPEG pairs |
| #3 Contact Sheet v1 | Elevate because visual sanity is now a recommendation gate, not a nice-to-have |
| #4 Pre-v0.2 Hardening | Include Adobe MCP status boundary and atomic/report validation work |
| New issue | Adobe MCP dry-run bridge: validate planned develop keys, catalog resolution, proof exports, and ledger before claiming completion |
| New issue | Packaged Mac field-review CLI: bring SD-card prototype behavior into a repeatable source-controlled command |
