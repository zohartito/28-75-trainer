# Field Review CLI

`trainer2875 field-review` packages the field-test extra-photo selection logic into a repeatable CLI command. It reads a review JSON file, computes the trainer recommended set, prints a planned summary, and can write an Adobe MCP handoff JSON.

This is a bridge command. It does not run Lightroom, scan original photo folders, resolve catalog records, apply edits, export proofs, or claim completion.

## Usage

Run from the repository root on macOS with Python 3.10+ (see the README platform requirements).

```bash
python -m trainer2875 field-review reports/field-review.json \
  --slug sunlight-model \
  --adobe-mcp-out reports/adobe-mcp-handoff.json
```

The command prints a JSON summary to stdout:

```json
{
  "schema_version": "0.1",
  "status": "planned",
  "slug": "sunlight-model",
  "source_review_json": "reports/field-review.json",
  "item_count": 13,
  "recommended_count": 12,
  "recommended_set": [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
  "adobe_mcp_handoff": "reports/adobe-mcp-handoff.json",
  "lightroom_completion_claim_allowed": false
}
```

## Input Shape

The input must be a JSON object with an `items` list. Each item should use the shape already consumed by `trainer2875.field_review.recommended_set`:

```json
{
  "items": [
    {
      "plan": {"shot": 1},
      "role": "wide",
      "status": "candidate",
      "source": "/path/to/shoot/DSC00001.ARW",
      "metadata": {
        "filename": "DSC00001.ARW",
        "focal_length": 28,
        "orientation": "horizontal"
      },
      "image_analysis": {
        "tone": "balanced",
        "contrast": 150,
        "highlight_clip_pct": 0,
        "shadow_clip_pct": 0
      }
    }
  ]
}
```

Accepted roles are the current field-review roles: `wide`, `massing`, `facade`, and `tight`. Items with `status` of `ok` or `candidate` are eligible for recommendation.

## Adobe MCP Handoff

When `--adobe-mcp-out` is provided, the command writes the planned-only contract produced by `trainer2875.field_review.build_adobe_mcp_handoff`.

The handoff keeps Lightroom execution outside this package:

- top-level handoff status remains `planned`;
- photo statuses remain `planned`;
- catalog paths and UUIDs remain unresolved;
- `lightroom_completion_claim_allowed` remains `false`;
- Adobe MCP must own catalog resolution, write transactions, proof exports, and run ledger confirmation.

## Safety

The command reads only the review JSON. It does not inspect, copy, rename, delete, or write original photo files.

For file outputs, it reuses the trainer report output guards. It refuses image-like output paths, existing symlink outputs, symlinked output parents, and Adobe MCP handoff paths inside the inferred source photo folder.

The source folder is inferred from item `source` or `path` values, or from optional top-level folder hints such as `source_folder`, `review_folder`, `input_folder`, or `shoot_folder`.
