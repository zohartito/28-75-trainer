from __future__ import annotations

import io
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trainer2875.analysis import analyze_folder
from trainer2875.metadata import (
    MAX_FOCAL_LENGTH_MM,
    MAX_JPEG_METADATA_BYTES,
    MAX_JPEG_MARKERS,
    parse_jpeg_metadata,
    parse_xmp_focal_value,
    read_metadata,
)


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

    def test_invalid_xmp_numeric_values_warn_per_photo_and_do_not_cancel_folder_review(self) -> None:
        invalid_fields = {
            "overlong_dimension": {"PixelXDimension": "9" * 4_301},
            "infinite_focal": {"FocalLength": "9" * 4_300},
            "negative_dimension": {"PixelXDimension": "-7000"},
            "zero_focal": {"FocalLength": "0/1"},
            "out_of_range_product": {"PixelXDimension": "100000", "PixelYDimension": "100000"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, overrides in invalid_fields.items():
                raw = root / f"{name}.ARW"
                raw.write_bytes(b"raw placeholder")
                write_xmp_sidecar(raw, **overrides)
            valid = root / "valid.ARW"
            valid.write_bytes(b"raw placeholder")
            write_xmp_sidecar(valid, PixelXDimension="7000", PixelYDimension="4667", FocalLength="50/1")

            analysis = analyze_folder(root)

            self.assertEqual(len(analysis.photos), len(invalid_fields) + 1)
            by_name = {photo.path.stem: photo for photo in analysis.photos}
            for name in invalid_fields:
                self.assertIn("xmp_metadata_invalid", by_name[name].warnings)
            self.assertEqual(by_name["valid"].width, 7000)
            self.assertEqual(by_name["valid"].height, 4667)
            self.assertEqual(by_name["valid"].focal_length_mm, 50)
            self.assertNotIn("xmp_metadata_invalid", by_name["valid"].warnings)

    def test_malformed_xmp_sidecar_warns_per_photo_and_does_not_cancel_folder_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            malformed = root / "malformed.ARW"
            malformed.write_bytes(b"raw placeholder")
            malformed.with_suffix(".xmp").write_text("<not-closed>", encoding="utf-8")
            valid = root / "valid.ARW"
            valid.write_bytes(b"raw placeholder")
            write_xmp_sidecar(valid)

            analysis = analyze_folder(root)

            self.assertEqual(len(analysis.photos), 2)
            by_name = {photo.path.stem: photo for photo in analysis.photos}
            self.assertIn("xmp_metadata_unreadable", by_name["malformed"].warnings)
            self.assertEqual(by_name["valid"].focal_length_mm, 50)

    def test_xmp_focal_normalization_rejects_zero_and_out_of_range_integers(self) -> None:
        for value in ("0.4", "0.5", "1/999999"):
            with self.subTest(value=value):
                self.assertEqual(parse_xmp_focal_value(value), (None, True))

        self.assertEqual(parse_xmp_focal_value("0.6"), (1, False))
        self.assertEqual(parse_xmp_focal_value(f"{MAX_FOCAL_LENGTH_MM}.4"), (MAX_FOCAL_LENGTH_MM, False))
        self.assertEqual(parse_xmp_focal_value(f"{MAX_FOCAL_LENGTH_MM}.6"), (None, True))


class JpegMetadataParserTests(unittest.TestCase):
    def test_normal_metadata_path_parses_jpeg_once_for_dimensions_and_exif(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jpeg = Path(tmp) / "fixture.jpg"
            write_jpeg_with_exif_focal_length(jpeg, focal_length=75, width=6000, height=4000)
            with patch("trainer2875.metadata.parse_jpeg_metadata", wraps=parse_jpeg_metadata) as parser:
                metadata = read_metadata(jpeg)

            self.assertEqual(parser.call_count, 1)
            self.assertEqual((metadata.width, metadata.height, metadata.focal_length_mm), (6000, 4000, 75))

    def test_marker_free_payload_is_read_in_one_bounded_chunk(self) -> None:
        handle = CountingBytesIO(b"\xff\xd8" + b"x" * 100_000)

        metadata = parse_jpeg_metadata(handle)

        self.assertEqual(metadata.warnings, ("jpeg_metadata_invalid",))
        self.assertEqual(handle.read_calls, 2)
        self.assertEqual(handle.read_sizes, [2, 1])

    def test_parser_stops_at_sos_and_does_not_read_large_entropy_data(self) -> None:
        header = make_jpeg_with_sof(width=6000, height=4000)
        handle = CountingBytesIO(header + b"x" * (MAX_JPEG_METADATA_BYTES * 2))

        metadata = parse_jpeg_metadata(handle)

        self.assertEqual((metadata.width, metadata.height), (6000, 4000))
        self.assertEqual(metadata.warnings, ())
        self.assertEqual(handle.tell(), len(header))
        self.assertEqual(sum(handle.read_sizes), len(header))

    def test_sos_length_envelope_must_be_complete_before_termination(self) -> None:
        sof = make_jpeg_sof_segment(width=6000, height=4000)
        malformed_payloads = (b"\xff\xda", b"\xff\xda\x00", b"\xff\xda\x00\x01")
        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                metadata = parse_jpeg_metadata(io.BytesIO(sof + payload))
                self.assertEqual((metadata.width, metadata.height), (6000, 4000))
                self.assertEqual(metadata.warnings, ("jpeg_metadata_invalid",))

        valid = parse_jpeg_metadata(io.BytesIO(make_jpeg_with_sof(width=6000, height=4000)))
        self.assertEqual((valid.width, valid.height), (6000, 4000))
        self.assertEqual(valid.warnings, ())

    def test_malformed_length_and_marker_budget_fail_safely(self) -> None:
        malformed = parse_jpeg_metadata(io.BytesIO(b"\xff\xd8\xff\xe1\x00\x01"))
        over_budget = parse_jpeg_metadata(io.BytesIO(b"\xff\xd8" + b"\xff\xd0" * (MAX_JPEG_MARKERS + 1)))

        self.assertEqual(malformed.warnings, ("jpeg_metadata_invalid",))
        self.assertEqual(over_budget.warnings, ("jpeg_metadata_limit_exceeded",))

    def test_byte_budget_stops_before_a_segment_payload_that_would_exceed_it(self) -> None:
        segment = b"\xff\xe0\xff\xff" + b"x" * (0xFFFF - 2)
        handle = CountingBytesIO(b"\xff\xd8" + segment * 16)

        metadata = parse_jpeg_metadata(handle)

        self.assertEqual(metadata.warnings, ("jpeg_metadata_limit_exceeded",))
        self.assertLessEqual(handle.tell(), MAX_JPEG_METADATA_BYTES)

    def test_limited_jpeg_does_not_stop_later_photo_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "limited.jpg").write_bytes(b"\xff\xd8" + b"\xff\xd0" * (MAX_JPEG_MARKERS + 1))
            valid = root / "valid.jpg"
            write_jpeg_with_exif_focal_length(valid, focal_length=75, width=6000, height=4000)

            analysis = analyze_folder(root)

            self.assertEqual(len(analysis.photos), 2)
            by_name = {photo.path.stem: photo for photo in analysis.photos}
            self.assertIn("jpeg_metadata_limit_exceeded", by_name["limited"].warnings)
            self.assertEqual(by_name["valid"].focal_length_mm, 75)


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


def write_xmp_sidecar(raw: Path, **overrides: str) -> None:
    fields = {
        "PixelXDimension": "7000",
        "PixelYDimension": "4667",
        "FocalLength": "50/1",
    }
    fields.update(overrides)
    attributes = " ".join(f'exif:{name}="{value}"' for name, value in fields.items())
    raw.with_suffix(".xmp").write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:exif="http://ns.adobe.com/exif/1.0/">
  <Description {attributes} />
</x:xmpmeta>
''',
        encoding="utf-8",
    )


def make_jpeg_with_sof(width: int, height: int) -> bytes:
    return make_jpeg_sof_segment(width, height) + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"


def make_jpeg_sof_segment(width: int, height: int) -> bytes:
    sof_payload = b"\x08" + struct.pack(">HH", height, width) + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    sof = b"\xff\xc0" + struct.pack(">H", len(sof_payload) + 2) + sof_payload
    return b"\xff\xd8" + sof


class CountingBytesIO(io.BytesIO):
    def __init__(self, initial_bytes: bytes) -> None:
        super().__init__(initial_bytes)
        self.read_calls = 0
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        self.read_sizes.append(size)
        return super().read(size)


if __name__ == "__main__":
    unittest.main()
