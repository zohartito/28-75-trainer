# Program Update - 2026-05-11

## Where We Are

28-75 Trainer has a working local v0.1 loop and v0.1.1 safety hardening in the source repo. The live Mac field test pushed the product into v0.1.2 territory:

- Real SD-card import with 56 reviewed RAW frames from 112 RAW/JPEG card files.
- More-than-12 photo behavior as candidate pool, not failure.
- Role coverage targets: 3 wide/context, 3 massing/medium, 3 facade/detail-with-context, 3 tight/detail-compression.
- Lightroom should remain an execution layer, not the trainer's source of truth.
- Adobe MCP handoff must stay planned-only until catalog resolution, dry-run, application, proof export, and ledger confirmation happen.

## Current Roadmap Position

| Version | Status | Notes |
|---|---|---|
| v0.1 | Built | Mission, review folder, coaching report, next mission |
| v0.1.1 | Built | Output/path safety, schema checks, corrupt/empty-folder behavior, simulator coverage |
| v0.1.2 | Mostly built | Field-test docs, JPEG EXIF, spread recommendation logic, packaged `field-review`, planned Adobe MCP handoff, Lightroom fix sheet |
| v0.2 | Started | Evidence engine now has RAW metadata placeholders, decision buckets, similarity grouping, schema versions, local preview contact sheets, dry-run bridge, ledger contract validation, keeper recall, and hardening |
| v0.3+ | Planned | Blur, similarity, culling evidence, session memory, curriculum |

## What Changed From The Latest Findings

The recommendation bug was real. The 30-photo run and first 56-photo run produced the same recommended set:

`[1, 7, 11, 13, 14, 15, 17, 18, 19, 20, 21, 25]`

That was a product failure signal. A trainer that chooses the same early frames after 26 more photos are added is not coaching the whole shoot.

The source repo now includes the first seven roadmap items:

- EXIF/JPEG metadata fixtures and metadata source labels;
- contact-sheet HTML plus visual selection sanity flags;
- packaged `field-review` CLI for larger candidate-pool shoots;
- Adobe MCP dry-run validation for planned handoffs;
- metadata-only RAW/XMP intake with honest `raw_image_not_decoded` warnings;
- planned-only Lightroom Markdown/CSV fix-sheet export;
- pre-v0.2 hardening for atomic writes and nested JSON validation.

The GitHub issue sweep then added the first v0.2 evidence-engine slice:

- source-labeled `select`, `maybe`, `reject`, and `practice-evidence` decision buckets;
- conservative similarity grouping so near-duplicate frames compete before picks finalize;
- explicit schema versions for reports, field-review summaries, Adobe MCP handoffs, ledgers, contact sheets, and Lightroom plans;
- local-only contact sheet previews with original-overwrite guards;
- Adobe MCP execution ledger validation for `planned -> validated -> applied -> complete`;
- first-week practice path helpers and keeper-recall false-reject benchmarking.

The fixed automated SD-card run produced:

`[7, 11, 15, 16, 18, 19, 21, 27, 30, 36, 39, 54]`

The stricter visual-coach Adobe MCP handoff selected:

`[7, 15, 16, 21, 23, 27, 30, 31, 36, 39, 43, 54]`

## What To Add Next

1. Integrate field-review evidence directly into normal `trainer2875 review` HTML output.
2. Add true thumbnail generation or adapter-backed preview extraction instead of stdlib byte-copy previews.
3. Add a persisted session/history CLI around the new practice helper.
4. Add richer keeper manifests with user-marked must-keeps and override reasons.
5. Connect Adobe MCP to real proof exports and run ledgers once the execution layer is ready.

## GitHub Update Needed

GitHub should be updated with this source-controlled program state:

- roadmap updated for the stale-pick finding, seven-item execution pass, and GitHub issue sweep;
- source modules for field selection, contact sheets, Adobe MCP validation, metadata intake, Lightroom plans, decision buckets, schema versions, and practice helpers;
- tests for spread selection, planned handoff, dry-run validation, RAW placeholders, contact-sheet sanity, atomic reporting, decision buckets, similarity grouping, ledger transitions, keeper recall, and original-overwrite protection;
- issue updates for completed v0.2 evidence-engine slices and remaining integration queue.

Raw photos, SD-card copies, generated reports, and Lightroom proof artifacts should stay out of GitHub unless intentionally reduced to tiny fixtures.

## Recommended Subagents Next

| Subagent | Scope |
|---|---|
| Review-report integrator | Fold field-review decisions, similarity groups, contact sheets, and Lightroom notes into the normal `review` HTML/JSON path |
| Thumbnail adapter worker | Add real thumbnail extraction/resizing behind an adapter while keeping local-only/no-original-mutation guarantees |
| Practice CLI worker | Add `sessions`, `history`, and `next` commands around the versioned practice helper |
| Keeper-manifest worker | Add manifest file loading, user override capture, and richer false-reject reporting |
| Adobe execution worker | Connect validated ledgers to actual Adobe MCP proof export results when the execution layer is ready |
| Release manager | Keep publishing from clean product exports and update private GitHub issues/milestones |
