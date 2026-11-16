# Adobe MCP Dry-Run Bridge

The Adobe MCP bridge is a validation layer between 28-75 Trainer planning and any future Lightroom or Adobe execution. It does not call Lightroom, Adobe MCP, filesystem catalog tools, or export services. It reads a handoff dictionary and checks the limited field-presence, container, status, and setting-key rules listed below. It does not establish execution readiness.

## Boundary

28-75 Trainer owns:

- recommended photo selection;
- photo roles and beginner-readable edit intent;
- planned Lightroom develop settings using known keys;
- unresolved catalog placeholders before Adobe MCP resolves them.

Adobe MCP owns:

- catalog path and UUID resolution;
- virtual copies, snapshots, and write transactions;
- proof exports;
- run ledger confirmation;
- any completion claim.

## API

Use `trainer2875.adobe_mcp.dry_run_adobe_mcp_handoff(handoff)`.

The result is a dictionary:

| Field | Meaning |
|---|---|
| `ok` | `True` when no dry-run errors are present |
| `errors` | List of issue dictionaries with `code`, `path`, and `message` |
| `warnings` | List of non-blocking issue dictionaries with `code`, `path`, and `message` |
| `recommended_count` | Number of photos marked `recommended: true` |
| `unresolved_catalog_count` | Number of photos missing either `catalog_path` or `uuid` |

Catalog fields may be unknown before Adobe MCP resolution. The dry run reports unresolved catalog references as `catalog_unresolved` warnings, not errors.

## Validation Rules

| Rule | Blocking |
|---|---|
| Required top-level fields must be present: `handoff_type`, `schema_version`, `status`, `execution_boundary`, `shoot`, `selection`, `lightroom_develop_key_policy`, and `photos` | Yes |
| Top-level `status` must be `planned` | Yes |
| `photos` must be a list | Yes |
| Recommended photos must include `edit_intent` | Yes |
| `edit_intent.develop_settings_planned` must be a mapping | Yes |
| Develop settings must use `trainer2875.field_review.ALLOWED_DEVELOP_KEYS` | Yes |
| Preview-only or risky actions must remain outside executable develop settings | Yes |
| Missing `catalog_path` or `uuid` is allowed before resolution | No |

## Example

```python
from trainer2875.adobe_mcp import dry_run_adobe_mcp_handoff
from trainer2875.field_review import build_adobe_mcp_handoff

handoff = build_adobe_mcp_handoff(review, slug="field-test")
dry_run = dry_run_adobe_mcp_handoff(handoff)

if not dry_run["ok"]:
    raise RuntimeError(dry_run["errors"])
```

The dry run does not mutate the handoff input. A passing dry run means only that the listed checks found no errors. It does not validate supported schema versions, the contents of `execution_boundary`, or develop-setting value types and ranges. For example, an unknown schema version, a null execution boundary, or a dictionary-valued `Exposure2012` can pass. An execution layer must validate its own complete contract before using a plan. A pass is not proof that Lightroom edits, exports, or a run ledger exist.
