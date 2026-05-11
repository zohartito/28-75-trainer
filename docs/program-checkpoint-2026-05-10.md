# Program Checkpoint - 2026-05-10

## Product Idea

28-75 Trainer is strongest as a local, lens-specific deliberate-practice coach:

`mission -> real shoot -> local evidence -> coaching -> next mission -> measurable progress`

The product should not try to replace Lightroom, Photo Mechanic, Narrative Select, Aftershoot, Imagen, Capture One, or FastRawViewer. Those tools are stronger at cataloging, editing, ingest, culling, and delivery workflow. 28-75 Trainer should sit beside them and own the learning loop: what the files prove, what habit needs work, and what the photographer should shoot next.

The ambitious version is a professional training program for a 28-75mm zoom: evidence review, personal curriculum, reshoot comparison, trend history, and workflow handoff while preserving local trust.

## Current Roadmap Assessment

The roadmap does not need a structural rewrite. It already has the right arc:

| Version | Theme | Status |
|---|---|---|
| v0.1 | Local training loop | Built and test-backed |
| v0.1.1 | Trust hardening | Built and test-backed |
| v0.1.2 | Field-test intelligence | Partly built; needs extra-photo grouping ported into this repo |
| v0.2 | Evidence engine | Planned; not implemented |
| v0.3 | Focus, similarity, and culling evidence | Planned; not implemented |
| v0.5 | Practice system | Planned; not implemented |
| v0.7 | Professional workflow fit | Planned; not implemented |
| v1.0 | Reliable field coach | Planned; not field-proven |
| v2.0 | Studio-grade training platform | Ambitious north star |

The roadmap did need a product-management update. We have now made these gates explicit:

- Real user photo-folder benchmark.
- Correction learning as a first-class loop, not just a trust metric.
- First-week activation with three shoots.
- Dedicated repo/release boundary before GitHub publication.
- Pre-v0.2 hardening for nested JSON validation, atomic writes, and metadata scoring honesty.
- Field-test intelligence: more than 12 photos should become alternates/candidates, with a recommended balanced set.

## What Is Actually Built

| Area | Actual State |
|---|---|
| CLI | `mission`, `review`, and `report` commands |
| Missions | Default field-map mission plus wide/28mm and tele/75mm focus missions |
| Folder analysis | Recursive local scan, supported-extension filtering, symlinked image skip, SHA-256 hashing, filename focal/aperture/ISO tags, JPEG/PNG dimensions |
| Scoring | Volume, focal coverage, orientation variety, exact duplicates, metadata completeness |
| Coaching | Deterministic recommendations and next mission |
| Reports | HTML and JSON reports with schema version, escaping, loaded-report validation, and output path safety |
| Tests | 24 unittest cases |
| Simulator | Six synthetic scenarios: balanced, missing metadata, exact duplicates, unsupported-only, corrupt mixed, nested uppercase |
| Packaging | Python package metadata and console script |

## Verification Evidence

The checkpoint verification passed with these commands:

| Command | Result |
|---|---|
| `python -B -m unittest discover -s tests` | 24 tests passed |
| `python scripts/run_simulator.py reports/program-checkpoint-simulator` | Six simulator scenarios passed |
| `python -m trainer2875 mission --out <temp>/mission.md` | Mission file written |
| `python scripts/create_sample_shoot.py <temp>/sample-shoot` | Sample shoot written |
| `python -m trainer2875 review <temp>/sample-shoot --out <temp>/review.html --json-out <temp>/review.json` | Reviewed 4 recognized images; next mission was `75mm Compression Study` |
| `python -m trainer2875 report <temp>/review.json --out <temp>/review-copy.html` | HTML report regenerated |

## What Is Not Built Yet

- Full EXIF parser beyond JPEG focal length.
- RAW decoding or sidecar metadata.
- Contact sheet thumbnails.
- Blur/focus detection.
- Perceptual duplicate grouping.
- Decision buckets and override tracking.
- False-reject or keeper-recall benchmark.
- Session history, progress model, or `sessions`/`history`/`next` commands.
- CSV/XMP handoff, ratings bridge, config, filters, or progress output.
- Accessibility/print QA for HTML reports.
- UI, optional AI critique, or full curriculum.
- Extra-photo role grouping, recommended picks, and generated Lightroom Classic fix notes are not implemented in this repo yet.

## Recent Audit Findings

| Finding | Impact | Action |
|---|---|---|
| Loaded JSON validation is shallow | Malformed nested report data can still fail during rendering instead of producing a clean CLI error | Add nested schema validation before v0.2 report expansion |
| Review writes are not atomic | If the second output write fails, the first output can remain | Add temp-file and replace-on-success writes before richer report outputs |
| Metadata completeness can reward filename tags on unreadable files | Corrupt files can look more metadata-complete than they deserve | Tighten metadata scoring to require readable image evidence |
| No real folder benchmark exists | Synthetic fixtures prove behavior, not field usefulness | Create a user-approved real-folder benchmark before claiming field readiness |
| Parent Git root is unsafe for GitHub publication | Pushing the workspace root could expose unrelated local files | Publish from a dedicated `28-75-trainer` repo boundary |

## What To Add Next

1. Evidence Review Studio: EXIF/source labels, contact sheet v1, decision buckets, and correction capture.
2. Field-Test Intelligence: role grouping, extra-photo alternates, recommended 12-photo set, and Lightroom fix notes.
3. RAW metadata intake: the real shoot produced RAW frames, so JPEG-only metadata is not enough.
4. Pre-v0.2 hardening: nested JSON validation, atomic writes, and stricter metadata scoring on unreadable files.
5. First-week activation: three missions that teach 28mm context, 50mm normal seeing, and 75mm compression.
6. Keeper-recall benchmark: user-marked must-keep frames to measure false-reject risk.
7. Practice memory: session history, reshoot comparison, and next-mission selection from repeated misses.

## GitHub Status

GitHub should be updated, but not by pushing the current parent workspace.

Current GitHub status:

- Private repo created: https://github.com/zohartito/28-75-trainer
- Initial import was pushed from a clean export of `28-75-trainer/`.
- The parent `Playground` workspace still has no remote by design.
- Parent workspace contains many unrelated untracked files and long-path warnings, so it should not become the GitHub repo.

Safe publish path:

1. Keep publishing only the `28-75-trainer/` product boundary.
2. Use a dedicated local clone/export for GitHub updates.
3. Use GitHub issues #1-#5 as the near-term execution queue.
4. Open a draft PR after a stable feature-branch workflow exists.

## Recommended Subagents Next

| Subagent | Mission |
|---|---|
| Hardening worker | Implement nested JSON validation, atomic writes, and stricter metadata scoring for unreadable files |
| Metadata worker | Add real JPEG EXIF/source-label adapter and fixtures |
| Report builder | Build contact sheet v1 and verify generated HTML |
| Benchmark designer | Define real-folder and keeper-recall benchmark protocol |
| Curriculum designer | Draft the first-week three-shoot activation path and later named tracks |
| Release manager | Create/push dedicated GitHub repo only after repo target is confirmed |
