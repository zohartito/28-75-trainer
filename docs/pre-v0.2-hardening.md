# Pre-v0.2 Hardening

Roadmap item 7 focuses the report boundary before v0.2 expands the evidence engine.

## Completed in Worker F

| Area | Hardening |
|---|---|
| Report writes | `write_text_output` now writes to a temporary file in the output directory, flushes it, and replaces the destination only after the temp write succeeds. Existing output-path guards still run first. |
| Failed writes | If the temp write fails, the prior destination file is preserved and the temporary artifact is removed. |
| Nested report JSON | `validate_report_data` now validates nested mission, analysis, scorecard, and next-mission fields before rendering. |
| Generated-schema compatibility | Full generated report sections are checked for generated fields such as mission metadata, analysis `root_name`, photo `relative_path`, and scorecard `missing_focal_lengths`. Existing minimal render fixtures remain accepted. |

## Validation Boundary

The validator keeps the v0.1 report boundary conservative:

- Core render fields remain required for loaded reports: mission title/objective, analysis photos and unsupported files, scorecard totals/components/observations/duplicate groups, recommendations, and next-mission title/objective.
- Generated report sections receive stricter checks when they include generated-schema markers.
- Photo rows now fail cleanly with `ValueError` if a photo object is missing `relative_path`, instead of failing later during HTML rendering.

## Remaining Concern

Metadata scoring honesty for unreadable files remains a roadmap concern outside this worker's ownership because it likely belongs in scoring or analysis code, not `trainer2875/reporting.py`.
