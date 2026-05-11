# Draft PR Description

## Summary

Ship 28-75 Trainer v0.1 as a local deliberate-practice CLI for photographers using a 28-75mm zoom.

The product loop is:

`mission -> review folder -> coaching report -> next mission`

This PR also documents the professional roadmap: a local, evidence-first training program that can grow from deterministic folder review into EXIF-backed reports, contact sheets, decision buckets, trust metrics, session history, calibrated image signals, and an optional studio-grade curriculum.

The latest competitive research reframes the roadmap around one product lesson: top tools win trust through visible reasons, grouping, overrides, fast visual evidence, and clean workflow handoff. 28-75 Trainer should learn those patterns without becoming a generic AI culling clone.

## What Shipped

- `trainer2875 mission` for Markdown/JSON practice missions.
- `trainer2875 review <folder>` for read-only folder analysis and HTML/JSON coaching reports.
- `trainer2875 report <review.json>` for regenerating HTML reports from JSON.
- Deterministic scoring for volume, focal coverage, orientation variety, exact duplicates, and metadata completeness.
- JPEG EXIF focal-length detection with filename tags as fallback.
- Beginner architectural-model field-test workflow for Mac, Adobe Bridge, and Lightroom Classic.
- Safety checks that refuse image-like report outputs and duplicate output paths before writing.
- Hardening checks that validate review outputs before scans, refuse report source/output overwrite, reject symlink output targets, and skip symlinked image inputs.
- Report schema validation and evidence-scope labels so loaded JSON cannot silently become a misleading coach report.
- Sample-shoot generator for repeatable local verification.
- Simulator runner for balanced, missing-metadata, exact-duplicate, unsupported-only, corrupt-image, and nested-uppercase folder cases.
- Tests for the core mission/review/report pipeline, output safety, schema validation, conservative coaching language, HTML escaping, and CLI failure behavior.
- Product docs:
  - `README.md`
  - `docs/roadmap.md`
  - `docs/research/competitive-learning-research-2026-05-10.md`
  - `docs/product-strategy-audit-2026-05-09.md`
  - `docs/github-update-2026-05-10.md`
  - `RETROSPECTIVE.md`
  - lifecycle scratchpad

## Verification

- `python -B -m unittest discover -s tests` - 24 tests OK.
- `python scripts/run_simulator.py reports/program-checkpoint-simulator` - six simulator cases OK.
- `python -m trainer2875 mission --out reports/mission.md`
- `python scripts/create_sample_shoot.py reports/sample-shoot`
- `python -m trainer2875 review reports/sample-shoot --out reports/sample.html --json-out reports/sample.json`
- `python -m trainer2875 review reports/sample-shoot --out reports/sample-json.html --json-out reports/sample-json.json --json`
- `python -m trainer2875 report reports/sample.json --out reports/sample-copy.html`
- Browser DOM check over `http://127.0.0.1:8765/reports/sample.html` confirmed score, reviewed file, unsupported file, and next mission.
- Original sample PNG hashes were unchanged before and after review.

## Known Limits

- v0.1 uses filename tags for focal length, aperture, and ISO.
- No full EXIF/RAW parser yet.
- JPEG EXIF focal length exists, but full EXIF, RAW, and sidecar metadata support do not.
- No blur/focus signal yet.
- No perceptual duplicate grouping yet.
- No contact sheet thumbnails yet.
- No decision-bucket or override-tracking UI/model yet.
- Extra-photo role grouping, recommended picks, and generated Lightroom fix sheets are roadmap items in this repo.
- No session history or persistent progress model yet.
- No remote is configured in the current workspace, and this branch has not been pushed.

## Next PRs

1. v0.1.2 Field-Test Intelligence: more-than-12 grouping, role assignment, recommended picks, and Lightroom fix notes.
2. RAW metadata intake and source labels.
3. v0.2 Evidence Engine: schema expansion, contact sheet v1, and report contracts.
4. Pre-v0.2 hardening: nested JSON validation, atomic paired writes, and metadata scoring honesty on unreadable files.
5. Decision buckets and trust metrics: `select`, `maybe`, `reject`, `practice-evidence`, override tracking, and false-reject risk.
6. Blur and similarity evidence with conservative thresholds and fixture-backed language.
7. Practice system: session history, three-shot proof, reshoot comparison, and progress-backed next missions.
8. Workflow handoff: CSV/JSON exports, sidecar-friendly annotations, filters, and progress output.
