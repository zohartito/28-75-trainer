# Lightroom Classic Fix Pass

Use this after the 28-75 Trainer report. The trainer tells you what happened in the practice set; Lightroom Classic helps polish selected images.

## Rule For This Test

Do not edit originals before running the trainer.

After the trainer report, edit in Lightroom Classic non-destructively and export finished copies. For the first test, avoid `Metadata > Save Metadata To File` on original JPEGs because Lightroom Classic can write metadata into JPEG/TIFF/DNG files. RAW files use sidecars more cleanly.

## Import

1. Open Lightroom Classic.
2. Import from:

   ```text
   ~/Pictures/28-75-field-tests/2026-05-10-arch-model-sunlight/originals
   ```

3. Use `Add` if the photos are already on your drive.
4. Do not rename during import for this first test.
5. Create a collection named `28-75 Arch Model Field Test`.

## Read The Trainer Report First

Open:

```text
~/Code/28-75-trainer/reports/arch-model-field-test.html
```

Use the report this way:

| Trainer Finding | Lightroom Action |
|---|---|
| Low focal coverage | Do not fix in Lightroom; repeat the shoot with missing focal lengths |
| Low orientation variety | Try crops for learning, but repeat the shoot with both horizontal and vertical frames |
| Exact duplicates | Mark one duplicate as reject or low rating |
| Metadata low | Check whether files are JPEG/RAW and whether EXIF is present |
| Strong structure score | Pick the best 1-3 images for final polish |
| More than 12 photos | Use Lightroom ratings to narrow to the best 1-3 from each focal-length block |

## Beginner Edit Recipe

For each selected image:

1. Enable `Remove Chromatic Aberration`.
2. Enable lens profile correction if Lightroom offers it.
3. Set white balance to `Auto` or `Daylight`.
4. Lower `Highlights` if sunlit surfaces are too bright.
5. Raise `Shadows` slightly if model recesses are too dark.
6. Adjust `Exposure` only a little.
7. Add small `Texture` or `Clarity` if edges look soft.
8. Use `Crop` to straighten and remove distracting background.
9. Use `Transform > Auto` or guided upright if verticals look tilted.
10. Export final images to:

   ```text
   ~/Pictures/28-75-field-tests/2026-05-10-arch-model-sunlight/exports
   ```

## What A Future App Should Do

The next professional-grade version should generate a Lightroom fix list from the trainer report:

- suggested keepers;
- duplicate rejects;
- missing focal-length reshoot notes;
- Lightroom collection name;
- edit checklist per image;
- optional XMP/sidecar or metadata handoff only after the safety model is settled.

## AI Agent Handoff

The current bridge is an AI-agent prompt plus generated plan files:

```text
docs/prompts/lightroom-ai-agent-prompt.md
reports/lightroom/lightroom-plan.json
reports/lightroom/lightroom-plan.csv
reports/lightroom/lightroom-plan.lua
```

Use the trainer JSON and the Lightroom plan files as the source of truth. The AI agent should convert them into exact Lightroom Classic steps for a beginner, while keeping all edits non-destructive.

For now, keep it manual and safe: trainer first, Lightroom second, exports separate.
