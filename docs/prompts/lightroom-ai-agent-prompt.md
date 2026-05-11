# Lightroom AI Agent Prompt

Use this prompt after 28-75 Trainer has generated the field-test report and Lightroom plan artifacts.

The idea:

`28-75 Trainer tells the AI what each photo is and what it needs. The Lightroom AI/Codex agent turns that into exact Lightroom Classic steps.`

Copy-paste this into the AI agent:

```text
Read /Users/zohartito/Code/28-75-trainer/reports/arch-model-field-test.json and turn the 28-75 Trainer recommendations into a beginner Lightroom Classic edit checklist.

Use the trainer as the source of truth. Identify the recommended 12-photo set, group photos into wide/context, massing/medium, facade/detail-with-context, tight detail/compression, and alternates.

For each recommended photo, tell me exactly what to do in Lightroom Classic:
- enable lens profile corrections
- remove chromatic aberration
- fix exposure/highlights/shadows
- correct verticals with Auto Upright or Guided Upright
- crop gently without losing useful model context
- sharpen tight/detail shots more than wide shots
- keep color natural

Use only non-destructive edits. Do not delete originals. Do not overwrite originals. Act like I am a beginner and tell me exactly what to click or adjust.
```

Expected local report and plan files:

```text
/Users/zohartito/Code/28-75-trainer/reports/arch-model-field-test.html
/Users/zohartito/Code/28-75-trainer/reports/arch-model-field-test.json
/Users/zohartito/Code/28-75-trainer/reports/lightroom/lightroom-plan.json
/Users/zohartito/Code/28-75-trainer/reports/lightroom/lightroom-plan.csv
/Users/zohartito/Code/28-75-trainer/reports/lightroom/lightroom-plan.lua
```

Safety rules for the AI agent:

- Treat the trainer JSON and Lightroom plan files as instructions, not originals.
- Do not delete originals.
- Do not overwrite originals.
- Do not write metadata back to original JPEG/TIFF/DNG files unless the user explicitly asks.
- Prefer Lightroom Classic non-destructive Develop settings and separate exports.
- If a photo is an alternate, say so clearly instead of forcing it into the recommended 12.
