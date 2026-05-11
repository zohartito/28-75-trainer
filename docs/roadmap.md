# 28-75 Trainer Roadmap

## Product Thesis

28-75 Trainer should become a professional-grade deliberate-practice system for photographers who want to get genuinely better with a 28-75mm zoom. The product should not try to beat Lightroom, Photo Mechanic, Narrative Select, AfterShoot, or FastRawViewer at their strongest jobs. It should sit beside them and own a different loop:

`mission -> real shoot -> local evidence -> coaching -> next mission -> measurable progress`

The core promise is simple: after every practice shoot, the photographer should know what they practiced, what the files prove, what habit needs work, and what to shoot next.

## Product Pillars

| Pillar | Meaning | Product Standard |
|---|---|---|
| Local trust | Originals stay untouched and private by default | No mutation beside originals unless explicitly requested; no hidden network dependency |
| Evidence-first coaching | Every score must trace back to observable file, metadata, or report evidence | Reports show the inputs behind each conclusion |
| Deliberate practice | Missions are narrow, repeatable, and skill-specific | One focused correction per loop, not generic aesthetic critique |
| Workflow fit | The tool complements existing photo workflows | Folder-first, exportable JSON/HTML, future XMP/sidecar compatibility |
| Professional reliability | The CLI behaves predictably on real shoots | Tested failure modes, clear limitations, installable packaging, versioned data |

## Competitive Wedge

| Reference Class | What They Do Better | What 28-75 Trainer Should Learn | What 28-75 Trainer Can Own |
|---|---|---|---|
| Lightroom | Catalog, edit, AI masking, sharing, assisted culling | Respect metadata, ratings, and user workflow | Lens-specific practice history and next missions |
| Photo Mechanic | Fast ingest, metadata, contact sheets, culling speed | Stay folder-first and keyboard-friendly | Coaching from practice evidence rather than delivery workflow |
| AfterShoot / Narrative Select | AI culling, duplicate/expression triage, portrait review ergonomics | Make review decisions fast, visible, and reversible | Skill formation, not client delivery automation |
| FastRawViewer | RAW-accurate exposure/focus inspection and XMP workflow | Be technically honest about image signals | Translate evidence into repeatable practice |
| Photo challenge apps | Motivation, community prompts, habit momentum | Make missions fun and repeatable | Local post-shoot coaching with file-backed measurement |

## v0.1 Gate - Local Training Loop

Status: built and committed in `6ffc7ce`.

| Gate | Acceptance Criteria | Status |
|---|---|---|
| Mission | CLI emits a usable 28-75mm practice mission in Markdown or JSON | Built |
| Review | CLI scans a local folder read-only and handles unsupported files cleanly | Built |
| Coaching | Review generates scored observations, recommendations, and a next mission | Built |
| Reports | HTML and JSON outputs are generated from the same review model | Built |
| Safety | Original image bytes are not modified by tests or sample flow | Built |
| Validation | Unit/CLI tests cover happy paths and key failure modes | Built |

## v0.1.1 Gate - Trust Hardening

Status: built in the 2026-05-09 roadmap/audit pass.

| Gate | Acceptance Criteria | Status |
|---|---|---|
| Output preflight | `review` refuses bad output paths before scanning the photo folder | Built |
| Symlink output safety | Report outputs refuse existing symlink paths instead of writing through them | Built |
| Report self-overwrite safety | `report <review.json> --out <same review.json>` fails without destroying the JSON | Built |
| Symlink input safety | Symlinked image files are skipped rather than read through outside the reviewed folder | Built |
| Report truth | Loaded JSON reports require a schema shape, report labels identify evidence sources, and HTML states v0.1 limitations | Built |
| Corrupt/empty-folder scoring | Unreadable image headers do not earn focal coverage; unsupported-only folders score 0 with no-evidence language | Built |
| Simulator coverage | A local simulator runs balanced, missing-metadata, exact-duplicate, unsupported-only, corrupt, and nested-uppercase cases | Built |
| Regression coverage | Tests cover safety, schema validation, conservative wording, and simulator-adjacent scoring behavior | Built |

## v0.1.2 Gate - Field-Test Intelligence

Status: partly built; roadmap updated from the first real architectural-model field test.

| Gate | Acceptance Criteria | Status |
|---|---|---|
| JPEG focal detection | JPEG EXIF focal length is read before filename fallback | Built |
| Field-test guide | Beginner architectural-model sunlight workflow exists with Mac, Adobe Bridge, and trainer paths | Built |
| Lightroom fix-pass guide | Manual Lightroom Classic post-report workflow exists | Built |
| Extra-photo handling | More than 12 photos are treated as alternates/candidates, not failures | Planned |
| Role grouping | Report groups likely wide/context, massing, facade/elevation, detail/context, tight detail, and compression candidates | Planned |
| Recommended picks | Report recommends a balanced 12-photo set from larger shoots | Planned |
| Lightroom fix sheet | Report gives per-photo Lightroom Classic starting steps | Planned |
| RAW metadata intake | RAW files expose focal length and basic metadata without mutating originals | Planned |

Exit test: a 30-photo architectural-model folder produces mission coverage, alternates, recommended 12 picks, missing-vertical warnings, and Lightroom fix notes while preserving originals.

## v0.2 Gate - Evidence Engine

Goal: make the report more truthful and more useful without overclaiming.

| Gate | Acceptance Criteria |
|---|---|
| Pre-v0.2 hardening | Nested report JSON validates cleanly, report writes are atomic, and metadata completeness does not reward unreadable files |
| Metadata adapter | Parse EXIF from JPEGs, RAW files or sidecars, with field-level source labels |
| Format honesty | Clearly distinguish counted formats from formats with full metadata support |
| Image signals schema | Extend the current top-level report schema into field-level source labels for dimensions, orientation, focal length, aperture, shutter, ISO, capture time, hash, and warnings |
| Contact sheet v1 | Generate local thumbnail sheets with filename, focal length, warnings, and score flags |
| Decision buckets | Add source-labeled `select`, `maybe`, `reject`, and `practice-evidence` buckets without implying artistic truth |
| Correction learning | Record user corrections/overrides as local training evidence without mutating originals |
| Trust metrics | Track false reject risk, override count, time to first useful insight, and next-mission specificity in test fixtures or review metadata |
| Report contracts | Add tests for contact-sheet rendering, metadata-source labels, unsupported files, and loaded-report rendering with new schema fields |
| Output safety | Document overwrite behavior and keep unsafe output combinations refused before writing anything |

Exit test: a real JPEG practice folder produces a report with metadata sources, a contact sheet, decision buckets with reasons, a JSON analysis schema version, and no original-file mutation.

## v0.3 Gate - Focus, Similarity, And Culling Evidence

Goal: move from folder metadata to practical image review signals.

| Gate | Acceptance Criteria |
|---|---|
| Blur heuristic | Add calibrated blur/focus scores with threshold versioning and conservative language |
| Similar sets | Add perceptual hash grouping for possible duplicates or burst candidates |
| Exact duplicates | Keep SHA-256 exact duplicate detection as a separate, stronger signal |
| Culling notes | Allow local keep/reject/needs-review annotations in a sidecar, never in originals |
| Keeper recall benchmark | Run fixtures or user-marked folders that include must-keep emotional/action frames and report false-reject risk |
| Visual evidence | Contact sheets show blur flags, similar-set IDs, and culling notes |

Exit test: exact duplicates, resized near-duplicates, intentionally blurred images, sharp images, and low-texture false-positive fixtures all produce explainable output.

## v0.5 Gate - Practice System

Goal: become a habit-forming coach rather than a one-off report generator.

| Gate | Acceptance Criteria |
|---|---|
| Session history | Persist local sessions with schema version and migration path |
| Weakness model | Choose next missions from repeated misses across sessions |
| Mission library | Add structured missions for wide context, normal perspective, compression, orientation pairing, movement, light, and selection discipline |
| Three-shot proof | Require repeatable evidence for practice missions, not one lucky frame |
| Reshoot comparison | Compare repeated missions across sessions and show what changed |
| First-week activation | Ship a guided first-three-shoot path: 28mm context, 50mm normal seeing, and 75mm compression |
| Progress report | Show trend lines for focal coverage, volume, metadata completeness, duplicate discipline, and mission completion |
| CLI ergonomics | Add `sessions`, `history`, and `next` commands |

Exit test: three reviewed shoots produce a history-backed next mission and a progress report without any cloud dependency.

## v0.7 Gate - Professional Workflow Fit

Goal: fit into a serious photographer's existing tools.

| Gate | Acceptance Criteria |
|---|---|
| Import/export | Export JSON/CSV and optionally sidecar-friendly annotations |
| Ratings bridge | Read common rating/label sidecars where available |
| Config | Support project config for output root, ignored folders, mission defaults, and report style |
| Performance controls | Add include/exclude filters, max-file guard, progress output, and size-first duplicate hashing |
| Packaging smoke | Install in a clean environment and run `trainer2875 --help`, mission, review, and report |
| Release boundary | Publish from a dedicated clean `28-75-trainer` repo or confirmed clean parent repo, never from a broad workspace root |

Exit test: a large nested folder can be reviewed with filters, progress output, and no accidental traversal of generated report folders.

## v1.0 Gate - Reliable Field Coach

Goal: a dependable local product that a serious photographer can use repeatedly.

| Gate | Acceptance Criteria |
|---|---|
| Local-first privacy | No network calls by default; clear export/import controls |
| Data migrations | Versioned session/report schema with migration tests |
| Calibrated signals | Blur/similarity thresholds are documented, fixture-tested, and user-overridable |
| Accessible reports | HTML reports pass automated accessibility checks and print cleanly |
| Release package | Installable package with changelog, support policy, and signed release notes if distribution requires it |
| Field validation | Tested on real practice folders supplied by the user |
| Real-folder benchmark | A user-approved benchmark set covers normal shoots, low-light failures, bursts, emotional keepers, bad files, and unsupported formats |

Exit test: installable v1.0 runs end-to-end on real user shoots and produces trustworthy, repeatable coaching without mutating originals.

## v2.0 Gate - Studio-Grade Training Platform

Goal: turn the local coach into a full training program while preserving local trust.

| Gate | Acceptance Criteria |
|---|---|
| Curriculum | Multi-week 28-75mm curriculum with progressive constraints and review rubrics |
| Personalization | Mission selection adapts to user history, subject interests, and failure patterns |
| Optional AI critique | Any AI-backed critique is opt-in, sourced, and separated from deterministic evidence |
| Mobile/desktop UI | Professional UI for missions, reports, contact sheets, and history |
| Coach mode | Exportable packages for mentors, workshops, or self-review programs |

Exit test: a user can complete a structured curriculum and see measurable improvement across repeated sessions.

## Immediate Next Milestones

| Priority | Milestone | Why Now |
|---|---|---|
| 1 | Real EXIF/JPEG metadata fixture path | Current filename-tag fallback is useful but not enough for real camera folders |
| 2 | Extra-photo role grouping | The real field test produced 30 frames, so the trainer must pick a balanced set from alternates |
| 3 | Lightroom Classic fix sheet | The next useful output is edit guidance after the trainer report, not a plugin yet |
| 4 | RAW metadata intake | The real field test produced RAW frames, so JPEG-only EXIF is not enough |
| 5 | Pre-v0.2 hardening | Audit found shallow nested JSON validation, non-atomic paired writes, and metadata scoring honesty gaps |
| 6 | Contact sheet v1 | Research confirms serious review tools win trust through fast visual evidence, not text-only tables |
| 7 | Decision buckets with source labels | Lightroom, Narrative, Imagen, and Aftershoot all train users to expect visible select/maybe/reject logic and overrideable reasons |
| 8 | Versioned analysis schema | Blur, similarity, history, and handoff features need a stable data spine |
| 9 | Session history and three-shot mission proof | The product becomes a coach only when it remembers prior misses and requires repeatable practice evidence |

## Research Inputs

The current competitive-learning research brief is in `docs/research/competitive-learning-research-2026-05-10.md`. Its main product change is this: v0.2 should be treated as an evidence engine, not a generic AI-culling sprint. The fastest path toward a professional-grade product is EXIF/source labels, contact sheets, decision buckets, and trust metrics before stronger blur, similarity, or AI critique claims.

## Current Position

As of the 2026-05-10 GitHub/roadmap update, the project is on branch `codex/28-75-trainer-v0-1`.

| Track | Status | Evidence |
|---|---|---|
| v0.1 local training loop | Built | Mission, review, coaching report, JSON, and next mission are implemented and tested |
| v0.1.1 trust hardening | Built | Output preflight, symlink safety, report schema checks, corrupt/empty-folder scoring, and simulator cases are implemented |
| v0.1.2 field-test intelligence | Partly built | Field-test docs, JPEG EXIF focal length, and Lightroom fix-pass docs exist; extra-photo grouping/picks need to be ported into this repo |
| Competitive research | Documented | `docs/research/competitive-learning-research-2026-05-10.md` converts market research into testable experiments |
| v0.2 evidence engine | Not started | Roadmap gates are defined, but RAW/source labels/contact sheets/decision buckets are not implemented yet |
| GitHub publication | Blocked on repo target | `gh` is authenticated, but no Git remote is configured and the parent Git root contains unrelated workspace files |

The current program checkpoint is documented in `docs/program-checkpoint-2026-05-10.md`.

## Program Metrics To Track

| Metric | Why It Matters |
|---|---|
| Original-file safety | Local trust is the product foundation |
| False reject risk | AI/culling tools lose trust when they hide emotional or action keepers |
| Override rate | User corrections reveal where scoring or grouping is wrong |
| Time to first useful insight | Professional tools win when review gets fast without becoming opaque |
| Next-mission specificity | The trainer only matters if it changes the next shoot |
| Real-folder pass rate | Synthetic fixtures are useful, but field folders decide whether the program is actually working |
