# Metadata Intake

28-75 Trainer uses a small stdlib-only metadata adapter in `trainer2875.metadata`.
It is intentionally conservative: it extracts evidence the tool can verify locally and
labels the field-level source used for each value.

## Field Sources

| Field | Supported Sources | Notes |
|---|---|---|
| Focal length | `exif`, `xmp_sidecar`, `filename`, `filename/raw_placeholder`, `raw_placeholder`, `unavailable` | JPEG EXIF is preferred, then RAW XMP sidecar metadata, then filename tags. RAW filename tags are marked as placeholders. |
| Dimensions | `jpeg_header`, `png_header`, `xmp_sidecar`, `raw_placeholder`, `unavailable` | JPEG/PNG dimensions come from headers. RAW dimensions only come from paired XMP sidecars today. |

## JPEG And PNG

JPEG files are parsed for APP1 EXIF focal length and JPEG SOF dimensions. PNG files
are parsed for IHDR dimensions. Neither path decodes image pixels or mutates
original files.

The explicit JPEG EXIF regression fixture path used in tests is:

`fixtures/real-exif-jpeg/sony-a7c2-75mm-exif.jpg`

## RAW Intake

Recognized RAW review candidates include `.arw`, `.cr2`, `.cr3`, `.dng`, `.nef`,
`.orf`, `.raf`, `.rw2`, `.pef`, and `.srw`.

RAW files are not decoded as images. The adapter may:

- Read a paired XMP sidecar with the same stem, using `.xmp` or `.XMP`.
- Extract straightforward XMP attributes such as `exif:FocalLength`,
  `exif:PixelXDimension`, and `exif:PixelYDimension`.
- Fall back to filename focal-length tags such as `75mm`.
- Emit `raw_image_not_decoded` so downstream reports do not imply RAW rendering,
  exposure analysis, sharpness analysis, or pixel-level inspection.

Paired XMP sidecars are treated as metadata sidecars during folder review rather
than unsupported photo files. Standalone XMP files remain outside the review set.
