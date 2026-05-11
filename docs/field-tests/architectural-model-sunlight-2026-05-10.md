# Field Test - Architectural Model In Sunlight

This is a beginner-friendly real-world test for 28-75 Trainer. The goal is to photograph an architectural model outside in sunlight, then run the v0.1 trainer on a safe copy of the photos.

## What The Trainer Can Check Today

28-75 Trainer v0.1 can check:

- whether you made enough photos;
- whether JPEG EXIF focal length or review-copy filename tags identify `28mm`, `35mm`, `50mm`, and `75mm`;
- whether you made both horizontal and vertical frames;
- whether exact duplicate files are present;
- whether image dimensions and focal tags are available.

It cannot yet judge whether the photo is beautiful, sharp, well exposed, or compositionally strong. We will use your human notes for that part.

## Before You Go Outside

1. Charge the camera or phone.
2. Clean the lens with a lens cloth or clean soft fabric.
3. Put the model on a stable surface.
4. Pick open shade or side sunlight if possible. Avoid harsh overhead noon sun if you can choose another time.
5. Keep the background simple: pavement, a neutral board, a table, or a plain wall is fine.
6. Do not worry about being good yet. The goal is to create useful evidence.

## Camera Setup

Use the simplest setup available:

- If using a dedicated camera: use `A`, `Av`, `P`, or Auto mode.
- If using a 28-75mm zoom lens: take groups at 28mm, 35mm, 50mm, and 75mm.
- If using a phone: do not pinch-zoom unless you have optical zoom choices. Instead, take the same shot from different distances and we will tag the review copies afterward.
- Use autofocus.
- Tap or focus on the model.
- Hold the camera with two hands.
- Take one breath, pause, then press the shutter.

## The 12+ Shot Mission

Take at least 12 photos total. More is fine and often better. If you shoot more than 12, keep working in blocks of three so the helper can tag the review copies clearly.

If you have a 28-75mm lens, start in this order:

| Shot | Focal | What to do |
|---|---:|---|
| 1 | 28mm | Wide view, model plus surrounding sunlight |
| 2 | 28mm | Wide view from lower angle |
| 3 | 28mm | Wide view from above or diagonal |
| 4 | 35mm | Three-quarter view of the main massing |
| 5 | 35mm | Move your feet, keep similar focal length |
| 6 | 35mm | Vertical frame |
| 7 | 50mm | Main facade or strongest elevation |
| 8 | 50mm | Detail plus context |
| 9 | 50mm | Vertical frame |
| 10 | 75mm | Tight detail: stairs, window, joint, entry, facade cut |
| 11 | 75mm | Same detail with different background distance |
| 12 | 75mm | Compression shot across the model |

Optional extras:

- One intentionally repeated shot to test exact-duplicate detection.
- One too-close/detail shot.
- One shadow-focused shot.
- One sunlight-edge shot where light grazes the model.

For more than 12 photos, continue the pattern:

- three more at 28mm from a new angle;
- three more at 35mm for massing;
- three more at 50mm for facade or elevation;
- three more at 75mm for detail/compression.

The trainer rewards enough useful repetitions. It does not require exactly 12.

## Human Notes To Capture

Write these down in your phone notes or Lumindec/Garmin:

- Date and time.
- Weather: clear, cloudy, mixed, windy.
- Sun direction: front, side, back, overhead.
- Which shot felt best.
- Which shot felt confusing or bad.
- One thing you changed while shooting.

## Best Paths On Your MacBook

Use this layout:

| Purpose | Path |
|---|---|
| 28-75 Trainer repo | `~/Code/28-75-trainer` |
| Untouched originals | `~/Pictures/28-75-field-tests/2026-05-10-arch-model-sunlight/originals` |
| Trainer review copies | `~/Code/28-75-trainer/field-shoots/2026-05-10-arch-model-sunlight/review-copy` |
| Trainer reports | `~/Code/28-75-trainer/reports/arch-model-field-test.html` and `.json` |

Why this layout:

- `~/Pictures/.../originals` keeps camera files outside Git.
- `field-shoots/` is ignored by Git and safe for review copies.
- `reports/` is ignored by Git and safe for generated reports.
- The trainer refuses to write reports inside the reviewed photo folder, so reports stay separate.

## Best Adobe + Mac Path

Use Adobe Bridge as the front door, then 28-75 Trainer as the coach.

Why Bridge first:

- It can import from a camera or phone on macOS.
- It gives fast thumbnails before we run the trainer.
- It can rename/export/contact-sheet later, but we will not let it modify originals for this test.

Avoid using Lightroom or Photoshop before the trainer review. Editing first changes the evidence. Use Lightroom/Camera Raw/Photoshop after the trainer if you want to make a final presentation image.

Recommended flow:

1. Shoot the 12-photo mission.
2. Open Adobe Bridge.
3. Choose `File > Get Photos From Camera` or, on macOS, `File > Import From Device`.
4. Import to:

   ```text
   ~/Pictures/28-75-field-tests/2026-05-10-arch-model-sunlight/originals
   ```

5. In Bridge, use thumbnails to confirm you have 12+ images and they are in shot order.
6. Do not delete from camera/card yet.
7. Do not rename originals in Bridge for this first test.
8. Run `scripts/prepare_field_test_review.py` to make safe review copies. The trainer can now read JPEG EXIF focal length, but tagged copies keep the first field test easy to inspect.
9. Run 28-75 Trainer on the review-copy folder.
10. Optional: after the trainer report, open the same folder in Lightroom Classic and try Assisted Culling as a comparison, not as the source of truth.

Lightroom Classic Assisted Culling can be useful for focus/exposure triage, but Adobe says the current early-access feature is optimized for portraits and headshots. Architectural model photos may not benefit as much. If you try it, write down where Lightroom disagrees with the trainer or your own eye.

Photoshop / Adobe Camera Raw should be the final polish step only. Pick the best one to three images after the trainer report, then use basic crop, exposure, white balance, shadows/highlights, and cleanup. Save edited exports separately from originals.

Adobe references:

- Bridge Photo Downloader: https://helpx.adobe.com/bridge/desktop/organize-and-find-files/organize-files-and-folders/import-photos.html
- Bridge overview: https://www.adobe.com/products/bridge.html
- Lightroom Assisted Culling: https://www.adobe.com/learn/lightroom-cc/web/ai-assisted-culling-lightroom
- Camera Raw Lens Blur: https://helpx.adobe.com/camera-raw/using/lens-blur.html

## Upload And Prepare The Review Folder

From the project folder on your Mac:

```bash
cd ~/Code/28-75-trainer
```

Create the folders:

```bash
mkdir -p ~/Pictures/28-75-field-tests/2026-05-10-arch-model-sunlight/originals
mkdir -p field-shoots/2026-05-10-arch-model-sunlight
mkdir -p reports
```

Copy your camera files into:

```text
~/Pictures/28-75-field-tests/2026-05-10-arch-model-sunlight/originals
```

Then make trainer-friendly review copies:

```bash
python3 scripts/prepare_field_test_review.py \
  ~/Pictures/28-75-field-tests/2026-05-10-arch-model-sunlight/originals \
  field-shoots/2026-05-10-arch-model-sunlight/review-copy
```

If `python3` is not available, try `python`.

### Windows Dev Path

If you run the same test from the Windows workspace, use this project folder:

```powershell
cd C:\Users\zohar_4ta16fp\Documents\Playground\28-75-trainer
```

Create a safe place for the shoot:

```powershell
New-Item -ItemType Directory -Force field-shoots\2026-05-10-arch-model-sunlight\originals
```

Copy your camera files into:

```text
C:\Users\zohar_4ta16fp\Documents\Playground\28-75-trainer\field-shoots\2026-05-10-arch-model-sunlight\originals
```

Then make trainer-friendly review copies:

```powershell
python scripts/prepare_field_test_review.py `
  field-shoots\2026-05-10-arch-model-sunlight\originals `
  field-shoots\2026-05-10-arch-model-sunlight\review-copy
```

The helper copies files into blocks:

- first 3 images -> `28mm`;
- next 3 images -> `35mm`;
- next 3 images -> `50mm`;
- next 3 images -> `75mm`.

If there are more than 12 images, it repeats that block pattern. That is why the shot order matters.

If the camera files already have JPEG EXIF focal length, the trainer can identify wide/medium/tele without the filename tags. The tags are still useful for this beginner test because they let you visually confirm the intended shot order in Finder, Bridge, and the report.

## Run 28-75 Trainer

Create a mission file:

```bash
python3 -m trainer2875 mission --out reports/arch-model-field-test-mission.md
```

Review the copied folder:

```bash
python3 -m trainer2875 review \
  field-shoots/2026-05-10-arch-model-sunlight/review-copy \
  --out reports/arch-model-field-test.html \
  --json-out reports/arch-model-field-test.json
```

Regenerate the report from JSON:

```bash
python3 -m trainer2875 report \
  reports/arch-model-field-test.json \
  --out reports/arch-model-field-test-copy.html
```

Open this report:

```text
~/Code/28-75-trainer/reports/arch-model-field-test.html
```

On macOS you can open it with:

```bash
open reports/arch-model-field-test.html
```

## What To Look For In The Report

- Score near 100: good first test structure. Now we need real visual review.
- Low focal coverage: shot order or filename tagging did not match the mission.
- Low orientation variety: take more vertical and horizontal mixes next time.
- Duplicate warning: good, the exact duplicate detector saw repeated bytes.
- Metadata completeness low: expected if filenames or image headers were missing.

## After The Report

Send the report summary and your notes back into the next planning pass. The next mission should be based on what happened:

- If the wide photos feel messy: do a 28mm context mission.
- If the detail photos feel flat: do a 75mm compression mission.
- If everything feels random: do the same 12-shot mission again, slower.

Then use `docs/workflows/lightroom-classic-fix-pass.md` for the editing pass.
