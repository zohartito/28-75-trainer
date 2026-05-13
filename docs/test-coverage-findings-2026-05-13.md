# Test Coverage Findings - 2026-05-13

## Summary

Ran `coverage run --source=trainer2875 -m pytest` against the current branch.
All 52 tests pass. Line coverage is **76%** (1,224 statements, 291 missed).

| Module | Stmts | Cover |
|---|---:|---:|
| `__init__.py` | 2 | 100% |
| `models.py` | 76 | 99% |
| `contact_sheet.py` | 65 | 98% |
| `scoring.py` | 63 | 97% |
| `coaching.py` | 37 | 95% |
| `analysis.py` | 48 | 94% |
| `lightroom_plan.py` | 93 | 94% |
| `reporting.py` | 178 | 89% |
| `adobe_mcp.py` | 86 | 88% |
| `mission.py` | 20 | 85% |
| `metadata.py` | 267 | **79%** |
| `field_review.py` | 131 | **77%** |
| `__main__.py` | 3 | **0%** |
| `cli.py` | 78 | **0%** |
| `field_review_cli.py` | 77 | **0%** |

## Highest-priority gaps

### 1. CLI entrypoints have no integration tests (0%)

Neither `cli.py` nor `field_review_cli.py` is exercised through `main()`. The
existing `tests/test_field_review_cli.py` calls helpers directly. Uncovered:

- `run_mission`, `run_review`, `run_report`, `run_field_review`
- argparse subcommand wiring and defaults
- the `(FileNotFoundError, NotADirectoryError, ValueError) -> exit code 2`
  translation at `trainer2875/cli.py:71-73`

A handful of `main(["review", folder, ...])` smoke tests with a tmp folder
would close both files at once and pin the stdout/stderr/exit-code contract.

### 2. EXIF/TIFF/XMP parsing in `metadata.py` (79%, 56 missing lines)

The lowest coverage on the most security-relevant code: binary parsing of
untrusted files. Uncovered paths include:

- `jpeg_exif_payload` — APP1 segment scan
- `tiff_focal_length` — missing EXIF IFD pointer, wrong value type
- `tiff_unpackers` — the big-endian (`MM`) branch
- `read_tiff_ifd` — truncated buffers, malformed entry counts
- `read_rational_as_int` — zero denominator
- `jpeg_dimensions` — SOF marker variants
- the entire XMP sidecar path: `read_xmp_sidecar_metadata`, `parse_focal_value`
  rational form (`"50/1"`)

Add small binary fixtures: malformed JPEG, truncated APP1, big-endian TIFF,
zero-denominator rational, real `.xmp` sidecar.

### 3. Selection logic in `field_review.py` (77%, 30 missing lines)

These branches decide which photos land in the recommended set; regressions
are silent.

- `image_quality_score`: only the "balanced / horizontal / no-clip" path is
  hit. `status == "warn"`, `tone in {bright, dark, flat}`, contrast > 240,
  highlight_clip, shadow_clip, and `orientation == "vertical"` branches
  (`field_review.py:106, 113-116, 122-123, 134`) are uncovered.
- `pick_spread` tie-breaker fallback at `field_review.py:158-171` is dead
  code in the test suite — yet it is the path taken when bucket picks
  collide.
- `tone_settings` (`field_review.py:337-344`): only the default branch is
  hit; `dark`, `bright`, and `flat` are untested. These feed
  `develop_settings_planned` in the Adobe MCP handoff.

### 4. `adobe_mcp.dry_run_adobe_mcp_handoff` negative paths (10 missing lines)

Happy paths are well covered; the malformed-input branches the validator
exists to catch are not. Missing cases:

- non-mapping handoff (`adobe_mcp.py:41-48`)
- `photos` not a list (`adobe_mcp.py:71-78`)
- non-mapping photo entry (`adobe_mcp.py:89-96`)
- recommended photo missing `edit_intent` (`adobe_mcp.py:146-153`)
- non-string develop-setting key (`adobe_mcp.py:158-165`)

One parametrized test per error code would round this out.

### 5. Scripts directory is largely untested

`scripts/run_simulator.py` (231 lines) and `scripts/create_sample_shoot.py`
have zero coverage. `scripts/prepare_field_test_review.py` has one
subprocess-based smoke test in `test_pipeline.py`. The simulator is the dev
loop; a "runs to completion and writes the expected files" test would
prevent silent breakage during refactors.

### 6. Schema-version drift guards

`REPORT_SCHEMA_VERSION` and `FIELD_REVIEW_SUMMARY_SCHEMA_VERSION` are string
constants with no test pinning them. A trivial equality test prevents
accidental schema bumps from sneaking through.

## Cheap follow-ups

- Wire coverage into `pyproject.toml` (`[tool.coverage.run] source =
  ["trainer2875"]`) and add a `make coverage` or CI step so the number does
  not drift.
- Consider a property-style test for `recommended_set`: output is a subset of
  input shots, never exceeds per-role targets, and is order-independent for
  equivalent inputs.

## Reproducing

```
pip install coverage
coverage run --source=trainer2875 -m pytest
coverage report -m
```
