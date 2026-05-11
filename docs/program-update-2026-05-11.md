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
| v0.2 | Started | Evidence engine now has RAW metadata placeholders, contact-sheet sanity, dry-run bridge, and hardening; decision buckets/similarity remain |
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

The fixed automated SD-card run produced:

`[7, 11, 15, 16, 18, 19, 21, 27, 30, 36, 39, 54]`

The stricter visual-coach Adobe MCP handoff selected:

`[7, 15, 16, 21, 23, 27, 30, 31, 36, 39, 43, 54]`

## What To Add Next

1. Add source-labeled decision buckets: select, maybe, reject, and practice-evidence.
2. Add similarity grouping so near-duplicate architectural model views compete against each other.
3. Version the richer analysis/handoff schemas.
4. Upgrade contact sheets from metadata HTML to local image thumbnails.
5. Connect Adobe MCP proof exports and run ledgers once the execution layer is ready.

## GitHub Update Needed

GitHub should be updated with this source-controlled program state:

- roadmap updated for the stale-pick finding and seven-item execution pass;
- source modules for field selection, contact sheets, Adobe MCP validation, metadata intake, and Lightroom plans;
- tests for spread selection, planned handoff, dry-run validation, RAW placeholders, contact-sheet sanity, and atomic reporting;
- issue updates for completed v0.1.2 work and next v0.2 queue.

Raw photos, SD-card copies, generated reports, and Lightroom proof artifacts should stay out of GitHub unless intentionally reduced to tiny fixtures.

## Recommended Subagents Next

| Subagent | Scope |
|---|---|
| Decision-bucket worker | Add `select`, `maybe`, `reject`, and `practice-evidence` buckets with source-labeled reasons |
| Similarity worker | Add perceptual hashing or visual grouping so near-duplicates compete before picks are finalized |
| Schema worker | Version the richer review, handoff, Lightroom-plan, and contact-sheet schemas |
| Thumbnail contact-sheet worker | Build local image thumbnail sheets with no network assets and no original mutation |
| Adobe MCP ledger worker | Define proof export paths, execution ledger schema, and status transitions from planned to applied/complete |
| Release manager | Keep publishing from clean product exports and update private GitHub issues/milestones |
