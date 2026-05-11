# Competitive Learning Research - 2026-05-10

This brief turns the research sweep into concrete things 28-75 Trainer can test. The point is not to clone Lightroom, Photo Mechanic, Aftershoot, Narrative Select, Imagen, Capture One, FastRawViewer, PhotoPills, GuruShots, 52Frames, LensUp, ShutterCoach, or Framez. The point is to learn where the market has already trained photographers' expectations, then use that knowledge to build a better deliberate-practice loop.

## Executive Takeaway

The top-of-market tools are converging on speed, grouping, AI-assisted decisions, culling-to-editing handoff, and habit loops. They still leave an opening: they optimize post-production throughput or community engagement, not lens-specific skill formation.

28-75 Trainer should own:

1. A local-first loop: `mission -> shoot -> evidence -> coaching -> next mission`.
2. Reported reasons, not black-box verdicts.
3. Lens-specific practice history: what the photographer is actually doing with 28mm, 35mm, 50mm, and 75mm.
4. Safer AI posture: assist and explain, never silently discard or overwrite.
5. A bridge between planning tools and post-shoot evidence.

## What The Best Tools Teach Us

| Reference | What they do better than us | What we should learn | What they miss that we can own |
|---|---|---|---|
| Adobe Lightroom Assisted Culling | AI-backed select/reject filters, subject focus, eye focus, eyes open, exposure/misfire rejection, overrideable decisions, flags/ratings/labels, auto-stacking | Show decision reasons and confidence; keep overrides first-class; use grouping before judging individual frames | Does not teach the photographer what habit to practice next with a specific lens |
| Photo Mechanic | Fast ingest, contact sheets, ratings/color classes, metadata templates, keyboard-first culling, work while ingest runs | Contact sheets must be fast, legible, and useful without importing into a catalog | It is a delivery workflow tool, not a training coach |
| Capture One | Session/catalog workflow, Cull View, content-similarity grouping, Face Focus, ratings/tags, tethered capture | Group-first review and face/focus zoom are table stakes for serious review | It does not turn repeated misses into a curriculum |
| FastRawViewer | RAW-truth inspection, exposure/focus evaluation, histograms, XMP handoff | Be explicit about technical evidence and where it comes from | It is technical triage, not deliberate practice |
| Aftershoot | Local/offline culling/editing/retouching workflow, duplicate grouping, blur and closed-eye detection, Lightroom/Capture One handoff | Treat AI as a first-pass assistant that the photographer reviews and corrects | It optimizes client-delivery speed more than skill growth |
| Imagen | Cloud-based culling/editing pipeline, culling-in method, grouping/rating, edited previews, exact-count selects | Users want control over selection targets and a smooth path from cull to edit | Cloud dependency and post-production focus leave room for local practice evidence |
| Narrative Select | Fast RAW review, Scenes, Close-Ups, face/eye/focus assessment, instant transitions, Lightroom handoff | Show group context and close-up evidence in the review surface | It speeds culling but does not build a lens-specific training record |
| 52Frames | Weekly challenge rhythm, fresh-shot expectation, community accountability, stretch-zone prompts | Practice improves when the prompt is narrow, time-boxed, and repeated | Community validation is not the same as private evidence-based coaching |
| GuruShots | Game mechanics, rankings, missions, voting, feedback loops | Motivation mechanics work, but must be separated from skill truth | Popularity can distort learning; 28-75 Trainer can measure improvement privately |
| LensUp / ShutterCoach / Framez | AI critique, daily or weekly challenges, streaks, progress tracking, genre-aware feedback, personalized courses | The training loop should feel alive: lesson, mission, proof, feedback, reshoot | Many AI coaches are cloud-first and generic; we can stay local, evidence-labeled, and lens-aware |
| PhotoPills / TPE | Planning, sun/moon timing, field-of-view tools, saved plans, academy material | Missions can include planned constraints before the shoot | They help make the shot happen; they do not inspect the practice folder afterward |

## Experiment Backlog

These are practical tests we can run against our own app and, where the user has access, against competitor trials/manual workflows.

| Experiment | Inspired By | Test Method | Success Signal |
|---|---|---|---|
| Decision buckets with reasons | Lightroom, Aftershoot, Imagen, Narrative | Add `select`, `maybe`, `reject`, and `practice-evidence` buckets to synthetic reports; require reason strings and source labels | Report never asks the user to trust an unexplained decision |
| Override tracking | Lightroom, Aftershoot | Create a JSON sidecar model for user corrections without touching originals | The trainer can learn from false positives/false negatives |
| Group-first review | Lightroom auto-stacks, Capture One groups, Narrative Scenes, Project Kestrel | Build fixtures with exact duplicates, near-duplicates, bursts, resized copies, and exposure variants | Similar frames are reviewed as sets instead of isolated files |
| Contact sheet v1 | Photo Mechanic, Narrative, Capture One | Generate local thumbnails with filename, focal tag, warning badges, duplicate group, and score flags | A user can inspect the coaching evidence without opening another app |
| Technical truth mode | FastRawViewer, ExifTool, Pillow, OpenCV | Add EXIF source labels, dimensions, orientation, capture time, and conservative blur scores | Report language distinguishes facts from heuristics |
| Keeper recall benchmark | Aftershoot, Imagen, Narrative, Lightroom criticism | Ask the user to mark must-keep frames, then measure whether the trainer ever downranks them | False reject rate becomes a tracked product risk |
| Three-shot proof loop | LensUp, 52Frames | Require three fresh attempts for a mission before unlocking the next mission | The loop trains behavior, not just one lucky frame |
| Reshoot comparison | ShutterCoach, LensUp | Compare two sessions with the same mission and show what changed | User sees improvement from repeat practice |
| Planned-shot cards | PhotoPills, TPE | Add mission cards for 28mm context, 50mm normal view, 75mm compression, golden-hour direction, and subject distance | The mission starts before the folder review, then closes the loop afterward |
| Workflow handoff | Photo Mechanic, Lightroom, Capture One, Aftershoot, Imagen, Narrative | Export JSON/CSV first, then evaluate XMP sidecar compatibility later | The trainer complements the real photo workflow instead of becoming a silo |
| Performance guardrails | Photo Mechanic, Narrative, FastRawViewer | Simulate 1k, 5k, and 10k file folders with unsupported/corrupt/nested cases | Review is predictable and refuses dangerous scans cleanly |
| Accessibility report check | Professional report expectations | Run automated accessibility checks on generated HTML reports once browser tooling is available | Reports are readable, printable, and not just pretty |

## What To Test In The Market

Use manuals and videos as acceptance-test inspiration. Where trials are available and the user is comfortable installing them, run the same real photo folder through those tools and through 28-75 Trainer, then write down the gaps.

1. Lightroom Assisted Culling
   - Test: Run a folder through Assisted Culling, inspect Selects/Rejects, hover reasons/scores, override decisions, and auto-stack behavior.
   - Record: false rejects, whether reasons are clear, how much control the photographer has, whether it feels trustworthy.

2. Photo Mechanic
   - Test: Ingest or open a folder, use contact sheet, ratings/color classes, auto-advance, and metadata template workflow.
   - Record: time to first useful contact sheet, keyboard friction, metadata expectations, how fast it feels on a messy folder.

3. Capture One
   - Test: Use Cull View with groups and Face Focus on a portrait/burst set.
   - Record: whether grouping beats one-by-one review, what face/focus evidence is visible, how ratings/tags map to later editing.

4. FastRawViewer
   - Test: Inspect RAW exposure/focus/histogram behavior on technically mixed files.
   - Record: which technical signals should stay separate from creative coaching.

5. Aftershoot / Imagen / Narrative Select
   - Test: Run AI culling on a folder with deliberate emotional keepers, bad focus, similar frames, blinks, and action shots.
   - Record: false reject rate, duplicate winner quality, speed, review ergonomics, export/handoff clarity.

6. 52Frames / GuruShots / LensUp / ShutterCoach / Framez
   - Test: Follow a weekly or daily challenge loop for one cycle and compare it to our mission loop.
   - Record: what creates momentum, what becomes gimmicky, what feedback is too generic, what would help a serious 28-75 practice plan.

7. PhotoPills / TPE
   - Test: Build one planned 28-75 mission around light, field of view, or compression, then review the resulting folder.
   - Record: whether pre-shoot planning data makes the post-shoot report more actionable.

## Product Decisions From Research

1. v0.2 should prioritize evidence: real EXIF, contact sheets, source labels, and clearer report schema.
2. v0.3 should add grouping and blur/similarity heuristics, but with conservative language and thresholds that can be tested.
3. v0.5 should become a true practice system: session history, three-shot mission proof, reshoot comparison, and next-mission selection.
4. AI critique should wait until deterministic evidence is strong enough to anchor it. If added, it must be opt-in and labeled separately from file-derived facts.
5. We should benchmark trust, not just speed: false reject rate, override rate, time to first useful insight, and whether the next mission is specific enough to shoot.

## Source And Watch List

- Adobe Lightroom Assisted Culling: https://helpx.adobe.com/lightroom-classic/help/assisted-culling.html
- Adobe Lightroom Assisted Culling at Import: https://helpx.adobe.com/lightroom-classic/help/assisted-culling-at-import.html
- Aftershoot culling/editing workflow: https://support.aftershoot.com/en/articles/6673181-culling-editing-workflow-with-aftershoot
- Imagen Culling: https://imagen-ai.com/culling/
- Imagen culling help center: https://support.imagen-ai.com/hc/en-us/categories/35592171626141-Culling
- Narrative Select: https://narrative.so/select
- Narrative Select getting started: https://support.narrative.so/en/articles/6980386-getting-started-with-select
- Photo Mechanic ingest docs: https://docs.camerabits.com/support/solutions/articles/48000207409-ingesting-photos-with-photo-mechanic
- Photo Mechanic contact sheets: https://docs.camerabits.com/support/solutions/articles/48000207551-contact-sheets-an-overview
- Capture One culling docs: https://support.captureone.com/hc/en-us/articles/7185822431645-Culling-images
- FastRawViewer manual: https://www.fastrawviewer.com/usermanual
- PhotoPills user guide: https://www.photopills.com/user-guide
- The Photographer's Ephemeris: https://photoephemeris.com/en/
- GuruShots getting started: https://support.gurushots.com/support/solutions/articles/13000024721-getting-started
- 52Frames overview: https://fstoppers.com/originals/52frames-weekly-photo-challenge-improve-your-photography-one-week-time-622506
- LensUp: https://lensup.pics/
- ShutterCoach: https://shuttercoach.app/
- Framez AI Hub: https://framez.app/ai-hub/
- ExifTool: https://exiftool.org/
- ImageHash: https://pypi.org/project/ImageHash/
- OpenCV Laplace operator: https://docs.opencv.org/4.x/d5/db5/tutorial_laplace_operator.html
- Pillow docs: https://pillow.readthedocs.io/

## Notes For Future Implementation

- Do not copy Project Kestrel or any restrictive/noncommercial code into this project. Use it only as architectural precedent.
- Avoid noncommercial model weights in core product paths unless the project intentionally becomes noncommercial.
- Do not let AI-culling language imply artistic truth. The product should say "this file has evidence of X" and "try Y next," not "this photo is good/bad."
- Every market-derived feature should enter as a testable product claim before it becomes UI or CLI behavior.
