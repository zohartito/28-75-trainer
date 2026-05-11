# Field Test Findings - 2026-05-10

## What Happened

The first real architectural-model field test moved the project from synthetic fixtures into actual shooting behavior.

Observed field-test facts from the Mac workflow:

- The shoot produced 30 RAW frames, not just the planned 12.
- More than 12 photos is good. The product should treat extras as alternates/candidates, not as failure.
- The original planned 12-shot order did not map cleanly to focal-length intent.
- The set was all horizontal, so the planned vertical frames were missing.
- The trainer needs to identify likely shot role: wide/context, massing, facade/elevation, detail/context, tight detail, compression.
- The report needs Lightroom Classic fix instructions after the trainer review.

## Product Lesson

The mission should be a target structure, not a rigid file count.

Better behavior:

| Input | Product Response |
|---|---|
| 12 photos | Check whether the planned structure was followed |
| More than 12 photos | Group into roles, pick a balanced 12-photo set, and mark alternates |
| RAW files | Read metadata or use sidecars/previews without mutating originals |
| All horizontal frames | Recommend vertical reshoot, not Lightroom-only correction |
| Mixed/incorrect focal order | Identify actual focal lengths and explain expected vs actual |
| Strong candidates | Generate Lightroom Classic fix steps for polishing |

## Roadmap Changes From This Test

1. Add an extra-photo candidate model: mission coverage plus alternates.
2. Add role grouping: wide/context, massing, facade/elevation, detail/context, tight detail, compression.
3. Add recommended picks: choose the best balanced 12-photo set from a larger shoot.
4. Add Lightroom fix sheet: exposure, highlights, crop, perspective, lens correction, and export notes.
5. Prioritize RAW metadata support sooner because the real shoot produced RAW frames.
6. Keep original-file safety non-negotiable: no edits, deletes, or metadata writes to originals.

## Current Repo Reality

The current Windows branch has:

- field-test guide;
- Adobe Bridge workflow;
- Lightroom Classic manual fix-pass guide;
- JPEG EXIF focal-length parsing;
- review-copy helper;
- tests and simulator.

The Mac-side prototype reported role grouping, 12/12 coverage, alternates, picks, and Lightroom notes against 30 frames. That behavior should be reconciled and ported into this main repo before we call it shipped here.

## Next Product Slice

Ship v0.1.2 as **Field-Test Intelligence**:

- mission coverage vs extras;
- role assignment from focal length and order;
- candidate/alternate grouping;
- recommended 12-photo set;
- Lightroom Classic fix notes;
- RAW metadata intake plan or adapter.

Exit test: a folder with 30 photos produces a report that says `30 photos found`, identifies mission coverage, lists alternates, recommends 12 picks, flags missing verticals, and includes Lightroom fix notes without mutating originals.
