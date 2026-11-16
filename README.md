# 28-75 Trainer

28-75 Trainer is a local deliberate-practice tool for photographers using a 28-75mm zoom. It gives a mission, reviews a folder of images without modifying originals, writes coaching reports, and recommends the next mission.

## v0.1 Loop

1. Get a mission:

   ```bash
   python -m trainer2875 mission --out reports/mission.md
   ```

2. Shoot into a normal folder. Keep your originals where they are.

3. Review the folder:

   ```bash
   python -m trainer2875 review /path/to/shoot --out reports/review.html --json-out reports/review.json
   ```

4. Regenerate a report from JSON if needed:

   ```bash
   python -m trainer2875 report reports/review.json --out reports/review-copy.html
   ```

## What v0.1 Measures

| Signal | Source | Purpose |
|---|---|---|
| Shot volume | Supported image count | Confirms enough repetitions for practice |
| Focal-length coverage | JPEG EXIF focal length, or filename tags such as `28mm` or `75mm` | Checks whether the whole 28-75mm range was practiced |
| Orientation variety | Display dimensions (JPEG EXIF Orientation applied) | Encourages landscape/portrait variation |
| Exact duplicates | SHA-256 file hash | Flags selection discipline issues |
| Metadata completeness | Dimension and focal-length parse rate | Shows where stronger EXIF tooling should land next |

Supported image extensions are `.jpg`, `.jpeg`, `.png`, `.webp`, `.tif`, and `.tiff`. JPEG focal length and dimensions are parsed with the Python standard library. PNG dimensions are parsed with the Python standard library. WebP and TIFF files are counted and hashed, but dimensions are reported as unknown in v0.1. Aperture and ISO are filename-derived until a fuller EXIF dependency is introduced.

## Filename Tags

JPEG EXIF focal length is read automatically when available. If focal length is missing, add tags to filenames so v0.1 can coach focal-length coverage:

| Tag | Example |
|---|---|
| Focal length | `street_28mm_001.jpg` |
| Aperture | `portrait_75mm_f2.8_004.jpg` |
| ISO | `corner_35mm_iso400_009.jpg` |

## Safety

The reviewer refuses to write outputs inside the reviewed folder. It opens originals read-only, computes hashes and dimensions, and writes report files separately. Report outputs with photo-like extensions are rejected to avoid accidental overwrite of image originals.

Existing symlink report outputs are rejected, and symlinked image files in a reviewed folder are skipped. That keeps the read/write boundary local and predictable before the tool touches real shoot folders.

Generated JSON reports include a schema version and are validated before HTML is regenerated from them.

## Build, Test, Run

Requires **macOS** and Python 3.10 or newer; runtime uses no third-party packages. The filesystem safeguards require POSIX descriptor-relative, no-follow operations and macOS system-path aliases. Windows and Linux are not supported by this version. Clone the repository and run these commands from its root folder:

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
python -m trainer2875 mission
python scripts/create_sample_shoot.py reports/sample-shoot
python -m trainer2875 review reports/sample-shoot --out reports/sample.html --json-out reports/sample.json
python -m trainer2875 report reports/sample.json --out reports/sample-copy.html
python scripts/run_simulator.py reports/simulator
```

The full test suite uses pytest, including the weekly-progress tests that stdlib unittest discovery does not collect. Use `python -m pytest` from the repository root so the source checkout is importable.

The simulator creates synthetic shoot folders for balanced practice, missing metadata, exact duplicates, unsupported-only folders, RAW metadata sidecars, corrupt images, and nested uppercase filenames. It fails if the expected safety or scoring behavior regresses.

## Real Field Test

For the first real field test, use `docs/field-tests/architectural-model-sunlight-2026-05-10.md`. It walks through photographing an architectural model outside, keeping MacBook originals in `~/Pictures/28-75-field-tests/.../originals`, creating trainer-friendly focal-length review copies in ignored `field-shoots/`, and generating the report. The copy helper accepts raster images only and skips RAW/XMP; for RAW shoots, review the original folder with paired XMP directly as described in the guide. The field test requires at least 12 photos, but more is fine.

For the post-report editing pass, use `docs/workflows/lightroom-classic-fix-pass.md`. If using a Lightroom/Codex assistant, use `docs/prompts/lightroom-ai-agent-prompt.md`.

The 2026-05-11 field-test update adds source-controlled selection and handoff logic for the Mac prototype findings:

- `trainer2875.field_review.recommended_set(...)` picks a balanced 12-photo set across the whole shoot instead of taking the earliest valid frames.
- `trainer2875.field_review.build_adobe_mcp_handoff(...)` creates a planned-only handoff contract for Adobe MCP/Lightroom execution.
- `python -m trainer2875 field-review <review.json> --adobe-mcp-out <handoff.json>` turns a field-review JSON into a planned Adobe MCP handoff.
- `trainer2875.contact_sheet` and `trainer2875.lightroom_plan` produce deterministic review/contact and planned Lightroom fix-sheet artifacts.
- Lightroom completion remains outside this package until Adobe MCP resolves catalog entries, applies edits, exports proofs, and writes a ledger.

## Limitations

- RAW files are metadata-only in the core analyzer; RAW pixels are not decoded and reports emit `raw_image_not_decoded`.
- No blur detection beyond structural metadata and duplicate review yet.
- No perceptual duplicate grouping yet.
- Contact sheets are source-controlled deterministic HTML artifacts, but not image-thumbnail contact sheets yet.
- No Lightroom Classic plug-in or XMP write path yet; Adobe MCP handoff is planned-only.
- Coaching is deterministic rules-based, not model-backed.
