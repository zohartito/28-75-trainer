# Product Strategy And Audit - 2026-05-09

## The Idea

28-75 Trainer is strongest when it is not trying to be a photo editor, culling robot, or generic challenge app. Its best shape is a local practice coach for a very specific tool: the 28-75mm zoom.

The professional-grade version should feel like a training program, not a utility script. It should give the photographer a tight assignment, inspect the resulting folder, show the evidence, coach one or two habits, and assign the next repetition. The emotional promise is: "I know what to practice next because my files showed me."

## Current Product State

| Area | Current State | Evidence |
|---|---|---|
| Mission loop | Working | `trainer2875 mission` emits Markdown or JSON |
| Review loop | Working | `trainer2875 review <folder>` scans supported images read-only |
| Reports | Working | HTML and JSON outputs generated from one report model |
| Next mission | Working | Coaching chooses a next mission from current weaknesses |
| Safety | Stronger after this pass | Tests verify original bytes unchanged; image-like outputs, same output paths, source/output report overwrite, symlink output targets, and symlinked image inputs are guarded |
| Report truth | Stronger after this pass | JSON reports have `schema_version`; loaded reports are validated; HTML explains that v0.1 uses filenames, dimensions, hashes, and counts |
| Simulator | Working | `scripts/run_simulator.py` covers balanced, missing-metadata, exact-duplicate, unsupported-only, corrupt, and nested-uppercase folders |
| Metadata | Partial field-test support | JPEG EXIF focal length is parsed; aperture/ISO still use filename tags; no RAW/full EXIF yet |
| Visual evidence | Missing | No contact sheet thumbnails yet |
| Persistence | Missing | No session history or progress model yet |
| Release | Local prototype | Committed on local branch, no remote push or PR yet |

## What Has Worked

| Win | Why It Matters |
|---|---|
| Product-first build | The lifecycle sweep audited a real loop instead of theoretical plans |
| Local-only base | No network, cloud, account, or model dependency in v0.1 |
| Deterministic scoring | Every score can be inspected and tested |
| Report and JSON split | Humans get HTML; future tools get structured JSON |
| Safety preflight | Output path mistakes fail before report writes |
| Browser verification | Static report was opened through localhost and checked in the browser |
| Simulator verification | Synthetic shoot folders now catch corrupt-image, duplicate, unsupported-only, and nested-path regressions |
| Scratchpad discipline | Findings, risks, and recommendations are traceable |
| Safety audit became code | Subagent findings turned into trust-hardening tests and fixes instead of staying as notes |

## What Has Not Worked

| Failure | Impact | Fix Already Taken Or Needed |
|---|---|---|
| Early EXIF wording drift | Docs briefly implied metadata support that did not exist | Fixed README and roadmap wording |
| Partial-output edge | One valid output could be written before a later invalid path failed | Fixed by preflighting output paths |
| Real-folder filesystem edges existed | Symlink output/input and report self-overwrite risks could violate trust | Patched in v0.1.1 hardening pass |
| Report language overclaimed | The app sounded like it could judge composition or real capture metadata | Fixed by adding source labels and an evidence-limit note |
| Corrupt images earned score credit | Filename tags could cover focal targets even when dimensions were unreadable | Fixed by requiring readable dimensions for focal coverage |
| Empty folders scored too generously | No-evidence reviews looked partially successful | Fixed: unsupported-only folders score 0 and say there is not enough evidence |
| Simulator fixtures accidentally duplicated bytes | The perfect synthetic case scored low because placeholder files were exact duplicates | Fixed by making non-duplicate fixture files unique |
| Subagent cap handling | Completed agents still counted until closed | Log this rule and close agents before next batches |
| Roadmap was too thin | Did not communicate professional-grade ambition | Expanded roadmap through v2.0 |
| Reports lack visual proof | Tables are useful but not enough for photo coaching | Add contact sheet v1 next |

## Recent Findings To Add

| Finding | Source | Product Response |
|---|---|---|
| No competitor owns lens-specific deliberate practice | Market scan | Keep the wedge narrow and deep |
| EXIF/RAW support should be optional and layered | Technical scan and field test | Keep standard-library JPEG focal length, then add RAW/sidecar adapters behind explicit extras |
| Blur and perceptual hashes are fragile signals | Technical scan | Use conservative language and fixture-tested thresholds |
| Report HTML needs stronger contracts | Test/security audits | Keep expanding report contract tests |
| Large folder scans could feel hung | Performance audit | Add filters, progress output, and faster duplicate strategy |
| JSON report rendering is a boundary | Security/boundary audits | Implemented: loaded report JSON now requires a v0.1 schema shape before rendering |
| Output validation happened after scan setup | 2026-05-09 audit | Implemented: review output validation now runs before folder analysis |
| `report input.json --out input.json` was not guarded | 2026-05-09 audit | Implemented: report regeneration refuses source/output same-path |
| Symlink output/input behavior needed coverage | 2026-05-09 audit | Implemented: symlink output targets are refused and symlinked image files are skipped as unsupported |
| Simulator was missing | 2026-05-09 audit | Implemented: six synthetic review scenarios now run as an expectation-checked gate |

## GitHub Recommendation

Yes, GitHub should be updated, but only after the user approves a push.

| Item | Status |
|---|---|
| Branch | `codex/28-75-trainer-v0-1` |
| v0.1 commit | `6ffc7ce5913db4d8912e466962a85bdb31c6dca5` |
| Remote | No remote is configured in this workspace |
| PR notes | `docs/pr-description.md` exists and should be used as the draft PR body |
| Push | Not done, because explicit permission is required |

Recommended PR framing: "Ship local v0.1 training loop and roadmap for professional-grade deliberate-practice coach."

## Recommended Next Build Order

| Order | Work | Acceptance Criteria |
|---|---|---|
| 1 | Field-level evidence schema | JSON identifies each signal source, not just top-level `schema_version` |
| 2 | Field-test intelligence | Extra-photo grouping, likely shot roles, balanced picks, and Lightroom fix notes |
| 3 | RAW/full metadata adapter | RAW/JPEG fixtures populate focal length, aperture, shutter, ISO, lens, and capture time where available |
| 4 | Contact sheet v1 | HTML report links or embeds local thumbnails with labels and warnings |
| 5 | Large-folder safeguards | Include/exclude filters, ignored reports folder, progress output, and max-file guard |
| 6 | Session history | Repeated reports produce history-backed next missions |

## Subagent Queue

| Subagent | Task | Output |
|---|---|---|
| Field-test worker | Port extra-photo grouping, recommended picks, and Lightroom fix notes into this repo | Code and tests |
| Metadata worker | Implement RAW/full EXIF adapter with fixtures and schema-source labels | Code and tests |
| Schema worker | Extend the existing schema gate into field-level evidence-source labels | Code and regression tests |
| Report builder | Build contact sheet v1 and HTML report integration | Code, sample report, browser verification |
| Safety reviewer | Audit traversal, symlinks, output roots, and overwrite behavior | Findings plus patch recommendations |
| Curriculum designer | Expand mission library into progressive 28-75mm curriculum | Structured mission JSON/Markdown |
| Release manager | Prepare GitHub push/PR once remote and permission exist | PR body, checklist, release notes |
