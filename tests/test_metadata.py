from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from trainer2875.analysis import analyze_folder


EXIF_JPEG_FIXTURE_PATH = Path("fixtures") / "real-exif-jpeg" / "sony-a7c2-75mm-exif.jpg"


class MetadataIntakeTests(unittest.TestCase):
    def test_jpeg_exif_fixture_reports_field_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / EXIF_JPEG_FIXTURE_PATH
            fixture.parent.mkdir(parents=True)
            write_jpeg_with_exif_focal_length(fixture, focal_length=75, width=6000, height=4000)

            analysis = analyze_folder(root)

            self.assertEqual(len(analysis.photos), 1)
            photo = analysis.photos[0]
            self.assertEqual(photo.relative_path, EXIF_JPEG_FIXTURE_PATH.as_posix())
            self.assertEqual(photo.focal_length_mm, 75)
            self.assertEqual(photo.focal_length_source, "exif")
            self.assertEqual(photo.width, 6000)
            self.assertEqual(photo.height, 4000)
            self.assertEqual(photo.dimensions_source, "jpeg_header")

    def test_raw_file_is_review_candidate_with_filename_placeholder_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "field_75mm_iso400.ARW"
            raw.write_bytes(b"not a decoded raw image")

            analysis = analyze_folder(root)

            self.assertEqual(analysis.unsupported_files, ())
            self.assertEqual(len(analysis.photos), 1)
            photo = analysis.photos[0]
            self.assertEqual(photo.extension, ".arw")
            self.assertEqual(photo.focal_length_mm, 75)
            self.assertEqual(photo.focal_length_source, "filename/raw_placeholder")
            self.assertIsNone(photo.width)
            self.assertIsNone(photo.height)
            self.assertEqual(photo.dimensions_source, "raw_placeholder")
            self.assertIn("raw_image_not_decoded", photo.warnings)
            self.assertIn("dimensions_unavailable", photo.warnings)
            self.assertNotIn("image_header_unreadable", photo.warnings)

    def test_raw_file_uses_xmp_sidecar_metadata_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "field_frame.ARW"
            raw.write_bytes(b"not a decoded raw image")
            (root / "field_frame.xmp").write_text(
                """<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:exif="http://ns.adobe.com/exif/1.0/">
  <rdf:RDF>
    <rdf:Description
      exif:FocalLength="50/1"
      exif:PixelXDimension="7000"
      exif:PixelYDimension="4667" />
  </rdf:RDF>
</x:xmpmeta>
""",
                encoding="utf-8",
            )

            analysis = analyze_folder(root)

            self.assertEqual(analysis.unsupported_files, ())
            self.assertEqual(len(analysis.photos), 1)
            photo = analysis.photos[0]
            self.assertEqual(photo.focal_length_mm, 50)
            self.assertEqual(photo.focal_length_source, "xmp_sidecar")
            self.assertEqual(photo.width, 7000)
            self.assertEqual(photo.height, 4667)
            self.assertEqual(photo.dimensions_source, "xmp_sidecar")
            self.assertIn("raw_image_not_decoded", photo.warnings)
            self.assertNotIn("dimensions_unavailable", photo.warnings)


def write_jpeg_with_exif_focal_length(path: Path, focal_length: int, width: int, height: int) -> None:
    tiff = build_exif_tiff_payload(focal_length)
    app1_payload = b"Exif\x00\x00" + tiff
    app1 = b"\xff\xe1" + struct.pack(">H", len(app1_payload) + 2) + app1_payload
    sof_payload = (
        b"\x08"
        + struct.pack(">HH", height, width)
        + b"\x03"
        + b"\x01\x11\x00"
        + b"\x02\x11\x00"
        + b"\x03\x11\x00"
    )
    sof = b"\xff\xc0" + struct.pack(">H", len(sof_payload) + 2) + sof_payload
    path.write_bytes(b"\xff\xd8" + app1 + sof + b"\xff\xd9")


def build_exif_tiff_payload(focal_length: int) -> bytes:
    exif_ifd_offset = 26
    rational_offset = 44
    return (
        b"II"
        + struct.pack("<H", 42)
        + struct.pack("<I", 8)
        + struct.pack("<H", 1)
        + struct.pack("<HHII", 0x8769, 4, 1, exif_ifd_offset)
        + struct.pack("<I", 0)
        + struct.pack("<H", 1)
        + struct.pack("<HHII", 0x920A, 5, 1, rational_offset)
        + struct.pack("<I", 0)
        + struct.pack("<II", focal_length, 1)
    )


if __name__ == "__main__":
    unittest.main()
