# Contact Sheet v1

`trainer2875.contact_sheet` provides a deterministic HTML contact sheet for reviewed item dictionaries. It is intentionally metadata-only: it does not open, decode, resize, copy, or modify image files.

## Public API

- `build_contact_sheet_html(reviewed, recommended_shots=None, title="28-75 Contact Sheet") -> str`
- `write_contact_sheet_html(reviewed, output_path, recommended_shots=None, title="28-75 Contact Sheet") -> Path`
- `visual_selection_sanity(reviewed, recommended_shots=None, min_selected_count_for_cluster=3, min_shot_span_ratio=0.25) -> dict`

## Contact Sheet Fields

The HTML table includes:

| Field | Source |
|---|---|
| Filename | `filename`, `metadata.filename`, or basename of `source_path` / `source` / `path` |
| Trainer Shot | `plan.shot` or `trainer_shot` |
| Role | `role` |
| Selection | `recommended_shots` membership, or item `recommended` when no set is supplied |
| Status / Warnings | `status` plus `warnings` |
| Notes | `notes` |

All displayed values are HTML-escaped.

## Visual Selection Sanity

The sanity helper returns a dictionary with `ok`, `flags`, selected-shot counts, shot span metrics, and duplicate details. It currently flags:

| Flag | Meaning |
|---|---|
| `shot_cluster_too_narrow` | At least three selected shots occupy less than 25% of the reviewed shot-number span |
| `duplicate_filenames` | More than one selected item resolves to the same filename |
| `duplicate_source_paths` | More than one selected item resolves to the same source path |

This is a preflight signal for human review, not a visual-quality claim. It only compares item dictionaries and shot numbers.

## Filesystem Behavior

`build_contact_sheet_html` performs no filesystem writes. `write_contact_sheet_html` writes only the caller-provided output path and does not touch original source paths.
