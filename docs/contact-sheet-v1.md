# Contact Sheet v1

`trainer2875.contact_sheet` provides a deterministic HTML contact sheet for reviewed item dictionaries. It supports local visual preview references without network assets. By default it references existing local source files; when `preview_assets_dir` is supplied to `write_contact_sheet_html`, it copies local preview assets into that generated folder.

The implementation intentionally does not decode or resize images. The Python standard library does not provide safe general-purpose raster thumbnail generation, so preview copies keep the original bytes and the HTML scales them visually with CSS.

## Public API

- `build_contact_sheet_html(reviewed, recommended_shots=None, title="28-75 Contact Sheet", source_root=None) -> str`
- `write_contact_sheet_html(reviewed, output_path, recommended_shots=None, title="28-75 Contact Sheet", source_root=None, preview_assets_dir=None) -> Path`
- `visual_selection_sanity(reviewed, recommended_shots=None, min_selected_count_for_cluster=3, min_shot_span_ratio=0.25) -> dict`

## Contact Sheet Fields

The HTML table includes:

| Field | Source |
|---|---|
| Preview | Local `source_path`, `source`, or `path`; network URLs are not rendered |
| Filename | `filename`, `metadata.filename`, or basename of `source_path` / `source` / `path` |
| Trainer Shot | `plan.shot` or `trainer_shot` |
| Role | `role` |
| Focal Length | `metadata.focal_length`, `metadata.focal_length_mm`, or `exif_hints.focal_length_mm` |
| Orientation | `metadata.orientation` or `exif_hints.orientation` |
| Pick State | `recommended_shots` membership, or item `recommended` when no set is supplied |
| Similarity Group | Optional; rendered only when a similarity group field is present |
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

`build_contact_sheet_html` performs no filesystem writes. `write_contact_sheet_html` writes the caller-provided output path and, only when `preview_assets_dir` is supplied, copied preview assets under that generated directory. Original source paths are never modified, and preview asset generation refuses to write inside an original source folder.
