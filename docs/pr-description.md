# Draft PR Description

## Summary

Ship the next 28-75 Trainer evidence-engine slice for field-review workflows.

The core product loop remains:

`mission -> review folder -> coaching report -> next mission`

This PR moves the roadmap from basic field-review handoff into a more trustworthy v0.2 evidence layer: visible decision buckets, similarity groups, schema contracts, local preview contact sheets, proof-ledger validation, practice-memory helpers, and keeper-recall measurement.

The latest competitive research reframes the roadmap around one product lesson: top tools win trust through visible reasons, grouping, overrides, fast visual evidence, and clean workflow handoff. 28-75 Trainer should learn those patterns without becoming a generic AI culling clone.

## What Shipped

- Source-labeled decision buckets: `select`, `maybe`, `reject`, and `practice-evidence`.
- Conservative similarity grouping that is separate from exact SHA-256 duplicates.
- Spread recommendation logic that avoids doubling up near-identical frames when alternatives exist.
- Schema-version helpers for report, field-review, Adobe MCP handoff/ledger, contact sheet, and Lightroom plan artifacts.
- Local-only contact-sheet previews with no network assets and guards against overwriting originals.
- Adobe MCP dry-run and execution-ledger validation without claiming Lightroom edits are complete.
- Planned Lightroom Markdown/CSV fix-sheet support.
- First-week practice path helpers and local session-history schema functions.
- Keeper-recall benchmark support for user-marked must-keep photos and false-reject risk.
- Regression tests for the reviewer-found safety issues: contact-sheet original overwrite, CLI keeper handoff, ledger schema versions, and top-level decision context in contact sheets.

## Verification

- `python -B -m unittest discover -s tests` - 94 tests OK.
- `python scripts/run_simulator.py reports/issue-sweep-simulator` - 7 simulator cases OK.
- `python -m trainer2875 --help`
- `python -m trainer2875 field-review --help`
- Artifact sanity script verified 12 recommended picks, Adobe MCP dry-run OK, `planned -> validated` transition OK, local contact-sheet preview copies, decision-context rendering, keeper recall, original-byte preservation, and refusal to overwrite an original with a contact sheet.

## Known Limits

- RAW support remains metadata-only; RAW pixels are not decoded.
- No blur/focus signal yet.
- Similarity grouping is conservative metadata/tone logic, not true perceptual hashing yet.
- Contact-sheet previews are local byte copies scaled in HTML/CSS, not resized raster thumbnails.
- Practice history exists as helpers/schema, not a persisted CLI yet.
- Lightroom edits are not applied; Adobe MCP execution remains outside this package until proof exports and ledger confirmation exist.

## Next PRs

1. Integrate field-review decisions, similarity groups, contact sheet, and Lightroom notes into the normal `review` HTML/JSON flow.
2. Add true image thumbnail generation or adapter-backed preview extraction.
3. Add persisted session CLI commands around the practice helper.
4. Add richer keeper-manifest loading and user override capture.
5. Connect Adobe MCP proof exports and real run ledgers when the execution layer is ready.
