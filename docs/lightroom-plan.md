# Lightroom Classic Fix Sheet Export

`trainer2875.lightroom_plan` turns a planned Adobe MCP handoff, or a review-like dictionary with recommended photos, into deterministic Markdown and CSV plan text for a Lightroom Classic fix pass.

The exporter is planning-only. It does not call Lightroom Classic, Adobe MCP, catalog APIs, sidecar writers, shell scripts, or image editors. It does not claim that any edit has been applied.

## Public Functions

```python
from trainer2875.lightroom_plan import lightroom_plan_to_csv, lightroom_plan_to_markdown

markdown = lightroom_plan_to_markdown(handoff, source_json_path="reports/lightroom/handoff.json")
csv_text = lightroom_plan_to_csv(handoff)
```

## Markdown Contract

The Markdown fix sheet includes:

- source JSON path when supplied;
- recommended set;
- planned-only boundary language;
- recommended photos grouped by role;
- per-photo beginner read, status, photo ID, steps, and Lightroom develop setting keys.

Role groups are ordered as wide context, massing medium, facade detail context, tight detail compression, then any unknown roles.

## CSV Contract

The CSV includes one row per recommended photo:

| Column | Meaning |
|---|---|
| `photo_id` | Stable trainer or handoff photo ID |
| `trainer_shot` | Trainer shot number |
| `filename` | Source filename or fallback shot label |
| `role` | Recommended role used for grouping |
| `setting_keys` | Semicolon-separated planned develop setting keys |
| `status` | Planned status from `edit_intent.status` or photo status |

## Input Shape

Preferred input is the Adobe MCP handoff produced by `trainer2875.field_review.build_adobe_mcp_handoff(...)`, especially its `photos`, `selection.recommended_set`, and `edit_intent.develop_settings_planned` fields.

For review-like dictionaries, the exporter also accepts `items` instead of `photos`. Recommended photos are selected from `selection.recommended_set`, top-level `recommended_set`, or `recommended: true` flags.

## Boundary

This exporter is a fix sheet, not an execution layer. Catalog resolution, virtual copies, snapshots, develop writes, proof exports, QA, and run ledgers remain outside this module until a separate dry-run and execution contract exists.
