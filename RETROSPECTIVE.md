# Retrospective

## 2026-05-08 v0.1 Build + Lifecycle Sweep

### What worked

- Building one real product slice first kept the lifecycle sweep anchored to code, reports, and tests.
- The local-only Python CLI was a good v0.1 shape: mission, review, coaching report, and next mission all work without network or cloud dependencies.
- The scratchpad helped separate product facts from audit findings, especially in a workspace with many unrelated untracked files.
- Browser verification over localhost was safer and more useful than trying to force direct `file://` access after the browser blocked it.

### What did not work

- The first subagent cap probe showed that completed agents still counted against the active limit until closed, so the second batch initially failed.
- Early docs overstated EXIF behavior; v0.1 actually uses filename tags for focal length, aperture, and ISO.
- The initial report write path could have produced partial output if a later output path failed validation.

### Why

- The repo was effectively empty for this product, so code had to exist before ship-readiness, security, and dead-code audits were meaningful.
- A broad sweep can create process drag quickly; the useful findings clustered into packaging honesty, output safety, report escaping, and test coverage.

### What we would do differently

- Close completed subagents before launching the next batch.
- Preflight all outputs before writing any report artifact.
- Keep the v0.1 contract plain: filename-tag metadata now; EXIF, blur, perceptual hashing, and contact sheets later.
- Apply the A3 rule immediately if lifecycle work starts producing more process than product.

## 2026-05-09 Strategy + Roadmap Pass

### What worked

- The strongest product idea became clearer: 28-75 Trainer should own lens-specific deliberate practice, not generic editing or culling.
- Updating the roadmap through v2.0 turned the project from a utility into a training program with gates, acceptance criteria, and a believable professional arc.
- The lifecycle findings were useful when clustered into product decisions: EXIF first, contact sheet next, schema before history, conservative blur/hash language.
- The second-pass hardening was worth doing immediately: validation now fails earlier, report regeneration cannot overwrite its own JSON source, and symlink behaviors are covered.
- Keeping GitHub as a recommendation instead of pushing was correct because no remote is configured and push permission was not granted.

### What did not work

- The first roadmap was too modest and read like a feature list rather than a product strategy.
- The current app still lacks real visual evidence; a photo coach without contact sheets will feel thin quickly.
- We still have no real user photo folder in the loop, so v0.1 is verified on synthetic fixtures rather than field material.
- A few hardening items only became obvious after the strategy pass, which means the roadmap should keep feeding back into engineering checklists.
- Loaded report JSON still needs schema validation before it becomes a stable long-term boundary.

### Why

- v0.1 intentionally stayed small to ship. That was right, but the roadmap had not yet absorbed the market and technical findings.
- The product needs a clear data spine before adding richer image intelligence, or later features will bolt on awkwardly.

### What we would do differently

- Treat every roadmap item as an exit test, not just a feature name.
- Add visual evidence before stronger coaching claims.
- Keep "local trust" and "evidence-first coaching" as non-negotiable product pillars.
- Pair every filesystem traversal/output change with symlink and overwrite regression tests.
- Prepare GitHub updates as draft artifacts until the user approves push and remote setup.

## 2026-05-09 Full Audit + Simulator Pass

### What worked

- Parallel audit agents found real issues instead of vague roadmap churn: malformed report JSON, corrupt image scoring, empty-folder scoring, overconfident wording, and output-path safety.
- The simulator caught a fixture design bug immediately: the "balanced" case reused byte-identical placeholder files, so the app correctly penalized exact duplicates.
- Making report language evidence-labeled improved trust: v0.1 now says it uses filenames, dimensions, hashes, and counts, not artistic judgment.

### What did not work

- Before this pass, loaded JSON could crash report generation with a traceback instead of a friendly schema error.
- Corrupt image files could still count toward focal coverage if the filename had a focal-length tag.
- Empty or unsupported-only folders could earn partial credit, which made a no-evidence review look more useful than it was.

### Why

- v0.1 intentionally avoided dependencies, so the tool only has lightweight signals. The app has to be very explicit about what those signals can and cannot prove.
- Fixture images need to model real review behavior. Exact-hash duplicate detection is literal, so repeated placeholder bytes are not a neutral detail.

### What we would do differently

- Add a simulator as soon as a folder-review product has more than one meaningful edge case.
- Treat every report phrase as a claim that needs a source label.
- Keep corrupt, empty, unsupported-only, duplicate, and nested-path folders in the permanent regression set.

## 2026-05-10 Competitive Research Pass

### What worked

- Splitting research lanes by workflow, AI culling, education/challenges, technical building blocks, and manuals/videos produced useful product signals quickly.
- The strongest market lesson was actionable: serious tools earn trust through visible reasons, grouping, contact sheets, overrides, and smooth handoff.
- Education and challenge apps clarified the real wedge: 28-75 Trainer should be a deliberate-practice loop, not another generic culling tool.

### What did not work

- Several market pages are marketing-heavy, so the best evidence came from manuals, help centers, and workflow videos rather than landing pages alone.
- AI-culling claims are easy to overread. Many tools say they save time, but photographer discussions still show anxiety around false rejects and emotional keepers.
- We still have no real user photo folder benchmark, so all recommendations remain product hypotheses until tested on real shoots.

### Why

- The market is mature around post-production speed, but thinner around local, evidence-labeled skill formation.
- Trust is the missing layer: photographers want help, but they also want to see and correct the reasoning before committing to a cull.

### What we would do differently

- Treat competitor research as experiment design, not feature shopping.
- Track false reject rate, override rate, time to first useful insight, and next-mission specificity as core product metrics.
- Build contact sheets and source labels before adding stronger AI critique language.

## 2026-05-10 GitHub + Roadmap Update

### What worked

- The roadmap now translates competitive research into concrete gates: EXIF/source labels, contact sheets, decision buckets, trust metrics, keeper-recall benchmarking, three-shot proof, and reshoot comparison.
- `docs/github-update-2026-05-10.md` captures the GitHub publish packet without pretending a remote exists.
- The program log is getting sharper: wins and failures are tied to operating rules, not vibes.

### What did not work

- GitHub could not be fully updated from this workspace because no Git remote is configured.
- The current Git root is the broader `Playground` directory, which contains many unrelated untracked files. Pushing it blindly would be unsafe.
- The product still has no real user photo-folder benchmark, so the roadmap is well-shaped but not field-proven.

### Why

- We have GitHub authentication, but not a confirmed repository target or clean repo boundary.
- The project started inside a shared playground workspace, which is good for fast iteration but poor for publishing unless we deliberately isolate the product.
- Professional program management requires recording blockers as plainly as wins.

### What we would do differently

- Start the product in its own Git repository before the first commit.
- Treat "remote configured and repo boundary clean" as a release gate, not an afterthought.
- Keep GitHub updates in a ready-to-publish packet until the target repo is confirmed.
- Do not push from a broad workspace root that contains unrelated files.

## 2026-05-10 Program Checkpoint

### What worked

- Parallel audits separated product strategy, implementation truth, and GitHub readiness cleanly.
- The product idea held up: a local, lens-specific practice coach is differentiated from editing, culling, and challenge apps.
- The current roadmap is strong enough to keep; it needed sharper release gates rather than a full rewrite.
- The implementation audit confirmed v0.1/v0.1.1 is real and test-backed, not just aspirational documentation.

### What did not work

- The GitHub release path is still blocked by the parent `Playground` repo boundary and missing remote.
- The roadmap did not explicitly name real-folder validation, correction learning, first-week activation, or release-boundary cleanup as gates.
- The code still has pre-v0.2 hardening gaps: shallow nested JSON validation, non-atomic paired report writes, and metadata scoring that can credit filename tags on unreadable files.
- Verification language drifted between the PR description and GitHub update packet.

### Why

- The product moved fast from empty repo to v0.1, so release management and field benchmarks lagged behind the working loop.
- Synthetic fixtures are excellent for safety regressions, but they cannot prove that a photographer will trust the report on real shoots.
- GitHub publishing needs a clean repository boundary, and this project currently lives inside a broader workspace.

### What we would do differently

- Create a dedicated repo boundary before the first product commit.
- Normalize verification commands in all publish docs at each checkpoint.
- Put real-folder benchmarking and user correction loops into the roadmap as gates as soon as the first loop works.
- Run a hardening worker before adding more photo-intelligence features.

## 2026-05-10 Real Field Test Prep

### What worked

- A concrete architectural-model sunlight shoot turned the abstract roadmap into a real beginner workflow.
- The v0.1 loop is usable for the field test if we keep originals untouched and create tagged review copies.
- The field-test guide makes the trainer honest: it explains what v0.1 can check and what it cannot judge yet.
- Adding a small copy/tag helper removes a beginner-hostile manual renaming step.

### What did not work

- The current trainer still needs filename focal tags because real EXIF parsing is not implemented.
- The trainer cannot yet evaluate sharpness, exposure, composition, or sunlight quality, even though those matter for this shoot.
- Uploading photos and preserving originals is still a manual workflow.

### Why

- v0.1 was intentionally built as a deterministic local loop before richer image intelligence.
- A true beginner field test exposes product friction faster than synthetic fixtures.
- Architectural model photography needs visual/contact-sheet feedback, which is still a v0.2+ roadmap item.

### What we would do differently

- Build a field-test packet alongside every new training mission.
- Add a safe review-copy workflow before asking users to rename or organize files.
- Prioritize contact sheet v1 and EXIF/source labels after the pre-v0.2 hardening slice.

## 2026-05-10 Adobe/Mac Field Workflow

### What worked

- Adobe Bridge is a strong match for the field test because it can import from device, show thumbnails, and keep the trainer workflow folder-first.
- Keeping Bridge before the trainer and Lightroom/Camera Raw/Photoshop after the trainer preserves clean evidence.
- The Adobe suite gives us a comparison path without forcing the trainer to pretend it has focus/exposure intelligence yet.

### What did not work

- Lightroom Assisted Culling is not the best primary tool for this architectural model test because current Adobe guidance says it is optimized for portraits and headshots.
- Any Adobe editing before review could blur the distinction between original field evidence and final presentation output.

### Why

- The trainer's v0.1 evidence model still depends on untouched files, copied review folders, and filename focal tags.
- Bridge complements that model; editing apps can distort it if used too early.

### What we would do differently

- Use Bridge as the default Mac import/thumbnail tool for real field tests.
- Run Lightroom/Camera Raw/Photoshop only after the trainer report unless the test is explicitly about comparing external culling tools.
- Log Adobe disagreements as product research for future focus/exposure/contact-sheet features.

## 2026-05-10 EXIF + Lightroom Direction

### What worked

- The field-test question exposed the right next product need: the trainer should identify wide/medium/tele from camera metadata, not rely on the user remembering.
- Adding JPEG EXIF focal-length parsing moves the product closer to real camera folders while keeping the no-dependency local design.
- The Lightroom Classic fix pass clarifies the product boundary: trainer first, edit/polish second.

### What did not work

- Aperture, ISO, RAW, and sidecar support are still not implemented.
- Lightroom handoff is still a manual workflow, not a plug-in, generated collection, or XMP sidecar flow.
- The trainer still cannot judge exposure, focus, sharpness, or composition quality.

### Why

- v0.1 started with filename tags to ship the loop before adding imaging dependencies.
- Real field use immediately made automatic metadata detection more important than another planning doc.

### What we would do differently

- Treat EXIF focal length as part of the beginner field-test baseline.
- Build Lightroom handoff as an action list before writing XMP or touching metadata.
- Keep original-file safety stricter than convenience until the handoff model is proven.

## 2026-05-10 Real Shoot Roadmap Update

### What worked

- The real shoot immediately exposed better product behavior: more than 12 photos should create alternates and picks, not punishment.
- The JPEG EXIF focal-length work points in the right direction: the trainer should infer shot type from files, not from the user's memory.
- The Lightroom Classic fix-pass idea is the right next product layer before a plugin.

### What did not work

- The Mac-side prototype reported role grouping, alternates, picks, and Lightroom notes, but that behavior is not yet ported into this main repo.
- The real shoot produced RAW frames, while this repo currently parses JPEG focal length only.
- The original 12-shot plan was too rigid for a beginner in the field.

### Why

- Real behavior is messier and better than the synthetic mission: people overshoot, miss verticals, and change focal lengths out of order.
- A professional training product needs to recover from that and organize the evidence.

### What we would do differently

- Treat the mission as structure and the folder as a candidate pool.
- Build role grouping and recommended picks before stronger scoring.
- Prioritize RAW metadata intake because field testing produced RAW files immediately.

## 2026-05-10 GitHub Publication

### What worked

- Publishing from a clean export of `28-75-trainer/` avoided the unsafe broad `Playground` root.
- The GitHub repo is private by default, which is the right posture before real photo workflows mature.
- Issues #1-#5 now mirror the immediate roadmap: field-test intelligence, RAW metadata, contact sheets, hardening, and practice memory.

### What did not work

- The parent workspace still has no clean remote and should not be treated as the release repo.
- The GitHub import starts as a clean product import rather than preserving the parent repo's full internal commit history.

### Why

- The parent workspace contains unrelated untracked files and long-path warnings.
- A product-only repo is easier to reason about, safer to share, and closer to how this should be developed going forward.

### What we would do differently

- Start the project in its own repository before the first commit.
- Keep GitHub publication tied to a dedicated local clone/export path.
- Use issues as the operating queue immediately after publishing.

## 2026-05-10 Lightroom AI Agent Prompt

### What worked

- The Lightroom agent prompt expresses the right product boundary: 28-75 Trainer decides what each photo is and what it needs; the AI agent translates that into Lightroom Classic steps.
- The prompt keeps beginner safety explicit: non-destructive edits, no deletes, no original overwrites.
- The expected plan artifacts now have stable paths: JSON, CSV, and Lua under `reports/lightroom/`.

### What did not work

- The Lightroom agent handoff is still manual. The repo documents the prompt but does not yet generate the plan artifacts in this branch.
- The Lightroom Lua path needs real Lightroom Classic validation before we treat it as executable workflow.

### Why

- This is the right intermediate step before a Lightroom plug-in: prove the edit checklist and plan schema before writing into Lightroom.

### What we would do differently

- Keep prompt, JSON plan, CSV plan, and Lua plan as separate artifacts so each can be tested independently.
- Treat Lightroom automation as an integration layer after the trainer report is trustworthy.

## 2026-05-11 Recommendation Bug And Adobe MCP Boundary

### What worked

- The live SD-card test caught a real product bug quickly: a 30-photo run and 56-photo run produced the same recommended 12, which made the order bias obvious.
- The fixed spread-selection test gave us a concrete regression guard instead of a vague "pick better photos" instruction.
- The contact-sheet review changed the product posture in the right way: EXIF and tone are useful hints, but visual coverage and subject variety must be explicit before Lightroom gets involved.
- The Adobe MCP boundary is now clearer: 28-75 Trainer can plan, but Adobe MCP owns catalog resolution, dry-run validation, execution, proofs, and ledger.

### What didn't

- The Mac prototype got ahead of the source repo, so product truth was split across local generated artifacts and GitHub source.
- The first recommendation logic was too order-driven and looked professional until a larger folder exposed the weakness.
- The Lightroom prompt was almost handed off too early, before the trainer recommendation set was re-evaluated.

### Why

- v0.1 optimized for shipping the loop, then real field behavior immediately exposed the next class of product risks.
- "Technically valid" is not the same as "good coverage of the actual subject."
- Training software needs a stricter boundary than editing software: it must say what it knows, what it inferred, and what still needs visual or execution proof.

### What we'd do differently

- Treat every generated recommended set as suspect until it passes a stale-list check against previous runs and a visual/contact-sheet sanity check.
- Promote Mac prototype fixes into source-controlled modules before telling another agent or Adobe layer to act on them.
- Keep all Lightroom and Adobe statuses as `planned` until an execution ledger proves otherwise.

## 2026-05-11 GitHub Issue Sweep

### What worked

- Six independent subagents moved real roadmap items in parallel: decision buckets, similarity grouping, schema versions, local contact previews, Adobe MCP ledger validation, and practice/keeper recall.
- The final reviewer caught actual integration bugs that the unit suite initially missed: contact-sheet output could overwrite a source path, keeper recall was not wired through the CLI, ledger schema versions were not validated, and contact sheets dropped top-level decision context.
- Regression tests now cover those misses directly.

### What didn't

- Several workers touched `field_review.py` and `contact_sheet.py`, so integration had real conflicts.
- The first merged version passed many tests while still missing important product-boundary behavior.
- Contact-sheet previews are still browser-scaled local copies, not true resized thumbnails.

### Why

- The roadmap items were related enough to share hot modules even though their goals were independent.
- Existing tests focused on each worker slice, not the combined report/handoff path.
- Staying standard-library-only avoided a dependency decision, but it limits thumbnail quality.

### What we'd do differently

- Add integration tests before merging subagent patches when multiple agents touch the same hot modules.
- Treat code review findings as first-class acceptance criteria, not cleanup.
- Keep "no original mutation" assertions on every output-producing feature, not just the main review command.

## 2026-05-11 Publish And Verification Slip

### What worked

- The clean-export PR check caught that the draft PR branch needed to be verified independently of the parent Playground workspace.
- The issue updates stayed private in `zohartito/28-75-trainer` and linked back to the draft PR.
- The incorrect export branch was corrected with a follow-up commit instead of being left as a deletion-only branch.

### What didn't

- Piping `git archive` directly into `tar` through PowerShell corrupted the binary archive stream.
- A final verification command was first run from the parent workspace, where `trainer2875` is not importable.
- The first PR branch commit was deletion-only and had to be corrected before review.

### Why

- The product is nested under `28-75-trainer/`, while the working Git repository is the larger Playground workspace.
- Windows PowerShell pipelines are not a safe default for binary archive streams.
- Package-level Python tests depend on running from the product root unless the package is installed.

### What we'd do differently

- Use file-backed archives or filesystem export from a known product root for Windows publishing.
- Run package verification from `28-75-trainer/` or install the package before invoking tests from another directory.
- Inspect the PR file list before creating or updating issue closure comments.
