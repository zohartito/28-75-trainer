# Session Log - 28-75 Trainer v0.1

## Objective

Ship a working local v0.1 training loop, then run a bounded lifecycle sweep against the actual project state.

## Shipped

- Python CLI package `trainer2875`.
- Commands:
  - `python -m trainer2875 mission`
  - `python -m trainer2875 review <folder> --out <html> --json-out <json>`
  - `python -m trainer2875 report <review.json> --out <html>`
- Deterministic pipeline:
  - CLI -> folder analysis -> scoring -> coaching -> HTML/JSON reports.
- Local safety:
  - Review reads originals and writes separate report files.
  - Image-like report output paths are refused.
  - Duplicate output paths are refused before any report write.
- Documentation:
  - `README.md`
  - `docs/roadmap.md`
  - `RETROSPECTIVE.md`
  - `.codex-scratchpad/28-75-trainer/findings.md`

## Verification Evidence

| Check | Command / Method | Result |
|---|---|---|
| Unit and CLI tests | `python -m unittest discover -s tests` | 9 tests OK |
| Mission command | `python -m trainer2875 mission --out reports/mission.md` | Wrote mission |
| Sample shoot | `python scripts/create_sample_shoot.py reports/sample-shoot` | Wrote 4 PNGs + 1 unsupported text file |
| Review command | `python -m trainer2875 review reports/sample-shoot --out reports/sample.html --json-out reports/sample.json` | Reviewed 4 supported images; wrote HTML/JSON |
| JSON output | `python -m trainer2875 review reports/sample-shoot --out reports/sample-json.html --json-out reports/sample-json.json --json` | Printed full JSON and wrote outputs |
| Report command | `python -m trainer2875 report reports/sample.json --out reports/sample-copy.html` | Wrote regenerated HTML |
| Report content | `Select-String` on `reports/sample.html` | Found title scaffolding, score, reviewed file, unsupported file, next mission |
| Browser report check | Temporary localhost server at `http://127.0.0.1:8765/reports/sample.html` | Browser DOM confirmed score, next mission, unsupported file, reviewed file |
| Bad output path | `python -m trainer2875 review . --out reports/bad.jpg --json-out reports/bad.json` | Failed safely |
| Missing folder | `python -m trainer2875 review no-such-folder ...` | Failed safely |
| File target | `python -m trainer2875 review pyproject.toml ...` | Failed safely |
| Unsupported-only folder | Temp folder with only `notes.txt` | Produced report with 0 supported, 1 unsupported |

## Lifecycle Sweep

- Observed platform cap: 6 concurrent subagents.
- Wave 1 covered orientation, roadmap, dead code, fabrication, dependency, market, technical precedent, test gaps, security, boundaries, ship readiness, and performance.
- Coordinator synthesis produced four actions; only the first three were implemented because v0.2 research should not expand v0.1.
- One reviewer checked the hardening patch and caught a partial-output edge; the edge was fixed and covered by tests.

## Deferred

- Real EXIF and RAW/sidecar parsing.
- Blur/focus scoring.
- Perceptual duplicate grouping.
- Contact sheets.
- Session history and persistent culling state.
- Large-folder progress/timing output.
- Full accessibility/i18n QA beyond static HTML basics.
