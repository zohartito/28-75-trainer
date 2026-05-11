# GitHub Update Packet - 2026-05-10

## Status

The GitHub CLI is authenticated, but the broad parent workspace should not be pushed directly:

- Current branch: `codex/28-75-trainer-v0-1`
- Git remote: none configured
- Git root: `C:\Users\zohar_4ta16fp\Documents\Playground`
- Product path: `28-75-trainer/`
- Risk: the Git root contains many unrelated untracked workspace files, so pushing the parent repository as-is would be unsafe.

GitHub should be updated from a dedicated GitHub repository for `28-75-trainer/`, or from a clean export of only that product folder. Do not push the broad `Playground` root.

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
| v0.1.2 Field-Test Intelligence | More-than-12 grouping, role assignment, balanced picks, Lightroom fix notes | A 30-photo shoot produces 12 recommended picks, alternates, missing-vertical warnings, and Lightroom notes |
| RAW Metadata Intake | RAW focal length and basic metadata without mutating originals | RAW architectural-model shoot reports actual focal lengths and roles |
| v0.2 Evidence Engine | EXIF/source labels, JSON schema expansion, contact sheet v1 | Real JPEG folder produces source-labeled report and contact sheet without mutating originals |
| Decision Buckets And Trust Metrics | `select`/`maybe`/`reject`/`practice-evidence` buckets, override tracking, false reject risk | Every decision has a reason and source label |
| Blur And Similarity Evidence | Conservative blur heuristic, perceptual duplicate grouping, exact duplicate separation | Fixture suite covers sharp, blurry, low-texture, exact duplicate, and near-duplicate cases |
| Practice System | Session history, three-shot proof, reshoot comparison, progress report | Three reviewed sessions produce a history-backed next mission |
| Workflow Handoff | CSV/JSON exports, sidecar-friendly annotations, ignored generated folders, progress output | Large nested folder can be reviewed with filters and clear handoff artifacts |

## Publish Checklist

1. Publish only the `28-75-trainer/` product folder, not the parent `Playground` root.
2. Prefer a private `zohartito/28-75-trainer` repository unless the user requests public.
3. Push the current product state.
4. Create issues from the suggested issue list above.
5. Open a draft PR only after there is a stable default branch and feature branch workflow.
