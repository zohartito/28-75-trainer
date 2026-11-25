from __future__ import annotations

import math
import re
import struct
from xml.parsers import expat
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

from .safeio import BoundedReader, MAX_FILE_BYTES, MAX_XMP_BYTES, file_identity, open_regular_file, verify_file_unchanged


FOCAL_RE = re.compile(r"(?<!\d)(?P<focal>\d{2,3})\s?mm(?![A-Za-z0-9])", re.IGNORECASE)
APERTURE_RE = re.compile(r"(?<![A-Za-z0-9])f[_-]?(?P<aperture>\d+(?:[._]\d+)?)", re.IGNORECASE)
ISO_RE = re.compile(r"(?<![A-Za-z0-9])iso[_-]?(?P<iso>\d{2,6})(?![A-Za-z0-9])", re.IGNORECASE)
RAW_IMAGE_EXTENSIONS = {".arw", ".cr2", ".cr3", ".dng", ".nef", ".orf", ".raf", ".rw2", ".pef", ".srw"}

# XMP sidecars are untrusted metadata accompanying images. These limits cover
# current high-resolution cameras while keeping conversions and arithmetic
# bounded before values reach the review pipeline.
MAX_XMP_INTEGER_DIGITS = 9
MAX_XMP_DECIMAL_FRACTION_DIGITS = 6
MAX_IMAGE_DIMENSION = 100_000
MAX_IMAGE_PIXELS = 500_000_000
MAX_FOCAL_LENGTH_MM = 2_000
MAX_XMP_ELEMENTS = 10_000
MAX_XMP_DEPTH = 128
MAX_XMP_FIELDS = 1_000
MAX_XMP_PARSE_CHUNK_BYTES = 4 * 1024
MAX_XMP_CHARACTER_DATA = MAX_XMP_BYTES
MAX_XMP_TEXT_VALUE_CHARS = 16 * 1024
XMP_METADATA_FIELDS = frozenset(
    {"PixelXDimension", "ImageWidth", "ExifImageWidth", "PixelYDimension", "ImageLength", "ExifImageHeight", "FocalLength"}
)
XMP_INTEGER_RE = re.compile(rf"\d{{1,{MAX_XMP_INTEGER_DIGITS}}}")
XMP_DECIMAL_RE = re.compile(
    rf"\d{{1,{MAX_XMP_INTEGER_DIGITS}}}(?:\.\d{{1,{MAX_XMP_DECIMAL_FRACTION_DIGITS}}})?"
)

# JPEG metadata must be available before Start Of Scan. Limit both consumed
# bytes and parsed markers so malformed files cannot turn metadata extraction
# into unbounded work.
MAX_JPEG_METADATA_BYTES = 1024 * 1024
MAX_JPEG_MARKERS = 4_096
JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


@dataclass(frozen=True)
class MetadataResult:
    width: int | None = None
    height: int | None = None
    dimensions_source: str = "unavailable"
    focal_length_mm: int | None = None
    focal_length_source: str = "unavailable"
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class XmpMetadata:
    width: int | None = None
    height: int | None = None
    focal_length_mm: int | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class JpegMetadata:
    width: int | None = None
    height: int | None = None
    exif_payload: bytes | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


def read_metadata(path: Path, *, handle: BinaryIO | None = None, review_root: Path | None = None) -> MetadataResult:
    suffix = path.suffix.lower()
    if suffix in RAW_IMAGE_EXTENSIONS:
        return raw_placeholder_metadata(path, review_root=review_root)

    warnings: tuple[str, ...] = ()
    focal_length: int | None = None
    if suffix in {".jpg", ".jpeg"}:
        jpeg = parse_jpeg_metadata(handle) if handle is not None else read_jpeg_metadata(path)
        width, height = jpeg.width, jpeg.height
        warnings = jpeg.warnings
        focal_length = tiff_focal_length(jpeg.exif_payload) if jpeg.exif_payload is not None else None
        if jpeg.exif_payload is not None and tiff_orientation(jpeg.exif_payload) in {5, 6, 7, 8}:
            width, height = height, width
    else:
        width, height = image_dimensions(path, handle=handle)
    dimensions_source = "unavailable"
    if width is not None and height is not None:
        if suffix == ".png":
            dimensions_source = "png_header"
        elif suffix in {".jpg", ".jpeg"}:
            dimensions_source = "jpeg_header"
        else:
            dimensions_source = "image_header"

    focal_length_source = "exif" if focal_length is not None else "unavailable"
    if focal_length is None:
        focal_length = infer_focal_length(path.name)
        if focal_length is not None:
            focal_length_source = "filename"

    return MetadataResult(
        width=width,
        height=height,
        dimensions_source=dimensions_source,
        focal_length_mm=focal_length,
        focal_length_source=focal_length_source,
        warnings=warnings,
    )


def raw_placeholder_metadata(path: Path, *, review_root: Path | None = None) -> MetadataResult:
    sidecar = read_xmp_sidecar_metadata(path, review_root=review_root)
    focal_length = sidecar.focal_length_mm if sidecar else None
    focal_length_source = "xmp_sidecar" if focal_length is not None else "raw_placeholder"
    if focal_length is None:
        focal_length = infer_focal_length(path.name)
        if focal_length is not None:
            focal_length_source = "filename/raw_placeholder"
    width = sidecar.width if sidecar else None
    height = sidecar.height if sidecar else None
    dimensions_source = "xmp_sidecar" if width is not None and height is not None else "raw_placeholder"
    return MetadataResult(
        width=width,
        height=height,
        dimensions_source=dimensions_source,
        focal_length_mm=focal_length,
        focal_length_source=focal_length_source,
        warnings=("raw_image_not_decoded", *(sidecar.warnings if sidecar else ())),
    )


def read_xmp_sidecar_metadata(path: Path, *, review_root: Path | None = None) -> XmpMetadata | None:
    sidecar = xmp_sidecar_path(path)
    if sidecar is None:
        return None
    try:
        with open_regular_file(sidecar, max_bytes=MAX_XMP_BYTES, root=review_root) as handle:
            identity = file_identity(handle)
            fields = stream_xmp_metadata(BoundedReader(handle, max_bytes=MAX_XMP_BYTES))
            verify_file_unchanged(handle, identity)
    except (OSError, expat.ExpatError, ValueError, OverflowError):
        return XmpMetadata(warnings=("xmp_metadata_unreadable",))
    width_value = fields.get("PixelXDimension") or fields.get("ImageWidth") or fields.get("ExifImageWidth")
    height_value = fields.get("PixelYDimension") or fields.get("ImageLength") or fields.get("ExifImageHeight")
    focal_value = fields.get("FocalLength")
    try:
        width, width_invalid = parse_xmp_dimension(width_value)
        height, height_invalid = parse_xmp_dimension(height_value)
        focal_length, focal_invalid = parse_xmp_focal_value(focal_value)
    except (ValueError, OverflowError):
        # The input is deliberately constrained before conversion, but this is
        # the final metadata boundary: a bad sidecar must never abort a batch.
        return XmpMetadata(warnings=("xmp_metadata_invalid",))

    dimensions_invalid = width_invalid or height_invalid
    if width is not None and height is not None and width * height > MAX_IMAGE_PIXELS:
        width = height = None
        dimensions_invalid = True
    warnings = ("xmp_metadata_invalid",) if dimensions_invalid or focal_invalid else ()
    return XmpMetadata(width=width, height=height, focal_length_mm=focal_length, warnings=warnings)


@dataclass
class _XmpFrame:
    name: str
    text_chunks: list[str] | None
    text_length: int = 0


class _XmpStreamCollector:
    """Collect only needed XMP fields without constructing an XML tree."""

    def __init__(self) -> None:
        self.fields: dict[str, str] = {}
        self.stack: list[_XmpFrame] = []
        self.elements = 0
        self.depth = 0
        self.character_data = 0

    def start_element(self, name: str, attributes: dict[str, str]) -> None:
        self.elements += 1
        self.depth += 1
        # These checks run in Expat's start callback, before any element node
        # is allocated or retained by application code.
        if self.elements > MAX_XMP_ELEMENTS:
            raise ValueError("XMP element limit exceeded")
        if self.depth > MAX_XMP_DEPTH:
            raise ValueError("XMP nesting depth exceeded")
        for key, value in attributes.items():
            field_name = local_name(key)
            if field_name in XMP_METADATA_FIELDS:
                self._store_attribute(field_name, value)
        field_name = local_name(name)
        self.stack.append(_XmpFrame(field_name, [] if field_name in XMP_METADATA_FIELDS else None))

    def end_element(self, name: str) -> None:
        if not self.stack:
            raise ValueError("XMP end element has no matching start")
        frame = self.stack.pop()
        if frame.name != local_name(name):
            raise ValueError("XMP element nesting is invalid")
        if frame.text_chunks:
            value = "".join(frame.text_chunks).strip()
            if value:
                self.fields.setdefault(frame.name, value)
        self.depth -= 1

    def character_data_handler(self, data: str) -> None:
        self.character_data += len(data)
        if self.character_data > MAX_XMP_CHARACTER_DATA:
            raise ValueError("XMP character data limit exceeded")
        if not self.stack or self.stack[-1].text_chunks is None:
            return
        frame = self.stack[-1]
        if frame.text_length + len(data) > MAX_XMP_TEXT_VALUE_CHARS:
            raise ValueError("XMP text value limit exceeded")
        frame.text_chunks.append(data)
        frame.text_length += len(data)

    def _store_attribute(self, field_name: str, value: str) -> None:
        if len(value) > MAX_XMP_TEXT_VALUE_CHARS:
            raise ValueError("XMP attribute value limit exceeded")
        self.fields[field_name] = value


def stream_xmp_metadata(reader: BoundedReader) -> dict[str, str]:
    """Parse a bounded XMP stream with Expat callbacks, never ElementTree."""

    collector = _XmpStreamCollector()
    parser = expat.ParserCreate(namespace_separator="}")
    parser.StartElementHandler = collector.start_element
    parser.EndElementHandler = collector.end_element
    parser.CharacterDataHandler = collector.character_data_handler
    parser.StartDoctypeDeclHandler = _reject_xmp_dtd
    parser.EntityDeclHandler = _reject_xmp_entity
    parser.UnparsedEntityDeclHandler = _reject_xmp_entity
    parser.ExternalEntityRefHandler = _reject_xmp_external_entity
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    while chunk := reader.read(MAX_XMP_PARSE_CHUNK_BYTES):
        parser.Parse(chunk, False)
    parser.Parse(b"", True)
    if collector.depth != 0 or collector.stack:
        raise ValueError("XMP element nesting is incomplete")
    return collector.fields


def _reject_xmp_dtd(*_: object) -> None:
    raise ValueError("XMP DTDs are not supported")


def _reject_xmp_entity(*_: object) -> None:
    raise ValueError("XMP entities are not supported")


def _reject_xmp_external_entity(*_: object) -> int:
    raise ValueError("External XMP entities are not supported")


def xmp_sidecar_path(path: Path) -> Path | None:
    for suffix in (".xmp", ".XMP"):
        candidate = path.with_suffix(suffix)
        # lstat only establishes presence; the descriptor open above performs
        # the authoritative no-follow check before any metadata is read.
        try:
            candidate.lstat()
        except FileNotFoundError:
            continue
        return candidate
    return None


def local_name(name: str) -> str:
    if "}" in name:
        return name.rsplit("}", 1)[1]
    return name.rsplit(":", 1)[-1]


def parse_int(value: str | None) -> int | None:
    parsed, _ = parse_xmp_dimension(value)
    return parsed


def parse_focal_value(value: str | None) -> int | None:
    parsed, _ = parse_xmp_focal_value(value)
    return parsed


def parse_xmp_dimension(value: str | None) -> tuple[int | None, bool]:
    if value is None or not value.strip():
        return None, False
    text = value.strip()
    if XMP_INTEGER_RE.fullmatch(text) is None:
        return None, True
    try:
        parsed = int(text)
    except (ValueError, OverflowError):
        return None, True
    if not 0 < parsed <= MAX_IMAGE_DIMENSION:
        return None, True
    return parsed, False


def parse_xmp_focal_value(value: str | None) -> tuple[int | None, bool]:
    if value is None or not value.strip():
        return None, False
    text = value.strip()
    parts = text.split("/")
    if len(parts) == 1:
        numerator_text = parts[0]
        denominator_text = None
    elif len(parts) == 2:
        numerator_text, denominator_text = parts
    else:
        return None, True
    if XMP_DECIMAL_RE.fullmatch(numerator_text) is None or (
        denominator_text is not None and XMP_DECIMAL_RE.fullmatch(denominator_text) is None
    ):
        return None, True
    try:
        numerator = float(numerator_text)
        denominator = float(denominator_text) if denominator_text is not None else 1.0
        focal = numerator / denominator
    except (ValueError, OverflowError, ZeroDivisionError):
        return None, True
    if not math.isfinite(focal):
        return None, True
    normalized = int(round(focal))
    if not 0 < normalized <= MAX_FOCAL_LENGTH_MM:
        return None, True
    return normalized, False


def infer_focal_length(filename: str) -> int | None:
    match = FOCAL_RE.search(filename)
    if not match:
        return None
    return int(match.group("focal"))


def infer_aperture(filename: str) -> str | None:
    match = APERTURE_RE.search(filename)
    if not match:
        return None
    return f"f/{match.group('aperture').replace('_', '.')}"


def infer_iso(filename: str) -> int | None:
    match = ISO_RE.search(filename)
    if not match:
        return None
    return int(match.group("iso"))


def image_dimensions(path: Path, *, handle: BinaryIO | None = None) -> tuple[int | None, int | None]:
    suffix = path.suffix.lower()
    try:
        if handle is None:
            with open_regular_file(path, max_bytes=MAX_FILE_BYTES) as owned_handle:
                return image_dimensions(path, handle=owned_handle)
        handle.seek(0)
        if suffix == ".png":
            return png_dimensions(handle.read(32))
        if suffix in {".jpg", ".jpeg"}:
            metadata = parse_jpeg_metadata(handle)
            return metadata.width, metadata.height
    except OSError:
        return None, None
    return None, None


def exif_focal_length(path: Path) -> int | None:
    if path.suffix.lower() not in {".jpg", ".jpeg"}:
        return None
    try:
        with open_regular_file(path, max_bytes=MAX_FILE_BYTES) as handle:
            payload = parse_jpeg_metadata(handle).exif_payload
    except OSError:
        return None
    if payload is None:
        return None
    return tiff_focal_length(payload)


def read_jpeg_metadata(path: Path) -> JpegMetadata:
    try:
        with open_regular_file(path, max_bytes=MAX_FILE_BYTES) as handle:
            return parse_jpeg_metadata(handle)
    except OSError:
        return JpegMetadata(warnings=("jpeg_metadata_unreadable",))


def jpeg_exif_payload(handle: BinaryIO) -> bytes | None:
    return parse_jpeg_metadata(handle).exif_payload


def parse_jpeg_metadata(handle: BinaryIO) -> JpegMetadata:
    """Read JPEG header segments once with exact, bounded reads.

    JPEG metadata lives before Start Of Scan. This parser keeps all marker work
    within fixed byte and marker budgets, stops at the end of a valid SOS
    header, and supplies dimensions plus the EXIF payload from one pass.
    """

    bytes_read = 0
    marker_count = 0
    width: int | None = None
    height: int | None = None
    exif_payload: bytes | None = None

    def read_exact(size: int) -> tuple[bytes | None, bool]:
        """Return (data, budget_exhausted) without reading beyond ``size``."""
        nonlocal bytes_read
        if size > MAX_JPEG_METADATA_BYTES - bytes_read:
            return None, True
        data = handle.read(size)
        bytes_read += len(data)
        if len(data) != size:
            return None, False
        return data, False

    def failure(limit_exceeded: bool) -> JpegMetadata:
        warning = "jpeg_metadata_limit_exceeded" if limit_exceeded else "jpeg_metadata_invalid"
        return JpegMetadata(width=width, height=height, exif_payload=exif_payload, warnings=(warning,))

    soi, limit_exceeded = read_exact(2)
    if soi is None or soi != b"\xff\xd8":
        return failure(limit_exceeded)

    while True:
        if marker_count >= MAX_JPEG_MARKERS:
            return failure(True)
        marker_prefix, limit_exceeded = read_exact(1)
        if marker_prefix is None:
            return failure(limit_exceeded)
        if marker_prefix != b"\xff":
            return failure(False)
        while True:
            marker_code, limit_exceeded = read_exact(1)
            if marker_code is None:
                return failure(limit_exceeded)
            if marker_code != b"\xff":
                break
            marker_count += 1
            if marker_count >= MAX_JPEG_MARKERS:
                return failure(True)
        marker = marker_code[0]
        marker_count += 1

        # Stuffed marker bytes only occur in entropy-coded data, which begins
        # at SOS. Treat one before SOS as malformed rather than scanning onward.
        if marker == 0x00:
            return failure(False)
        if marker == 0xD9:  # End Of Image.
            return JpegMetadata(width=width, height=height, exif_payload=exif_payload)
        if marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue

        length_bytes, limit_exceeded = read_exact(2)
        if length_bytes is None:
            return failure(limit_exceeded)
        segment_length = struct.unpack(">H", length_bytes)[0]
        if segment_length < 2:
            return failure(False)
        payload, limit_exceeded = read_exact(segment_length - 2)
        if payload is None:
            return failure(limit_exceeded)

        if marker == 0xDA:  # Start Of Scan: no further header metadata exists.
            if not valid_sos_payload(payload):
                return failure(False)
            return JpegMetadata(width=width, height=height, exif_payload=exif_payload)

        if marker in JPEG_SOF_MARKERS and len(payload) >= 5:
            height, width = struct.unpack_from(">HH", payload, 1)
            if width == 0 or height == 0:
                return failure(False)
        elif marker == 0xE1 and exif_payload is None and payload.startswith(b"Exif\x00\x00"):
            exif_payload = bytes(payload[6:])

def valid_sos_payload(payload: bytes) -> bool:
    """Validate the structural envelope of a JPEG Start Of Scan segment."""
    if not payload:
        return False
    component_count = payload[0]
    return 1 <= component_count <= 4 and len(payload) == 4 + 2 * component_count


def tiff_orientation(payload: bytes) -> int | None:
    unpack_short, unpack_long = tiff_unpackers(payload)
    if unpack_short is None or unpack_long is None or unpack_short(2) != 42:
        return None
    entry = read_tiff_ifd(payload, unpack_long(4), unpack_short, unpack_long).get(0x0112)
    if entry is None or entry[:2] != (3, 1):
        return None
    # A single SHORT is stored inline, in the first two bytes of the value field.
    value = entry[2] & 0xFFFF if payload[:2] == b"II" else entry[2] >> 16
    return value if 1 <= value <= 8 else None


def tiff_focal_length(payload: bytes) -> int | None:
    unpack_short, unpack_long = tiff_unpackers(payload)
    if unpack_short is None or unpack_long is None:
        return None
    if len(payload) < 8 or unpack_short(2) != 42:
        return None
    ifd0_offset = unpack_long(4)
    ifd0 = read_tiff_ifd(payload, ifd0_offset, unpack_short, unpack_long)
    exif_ifd_pointer = ifd0.get(0x8769)
    if not exif_ifd_pointer:
        return None
    pointer_type, pointer_count, exif_ifd_offset = exif_ifd_pointer
    if pointer_type != 4 or pointer_count != 1:
        return None
    exif_ifd = read_tiff_ifd(payload, exif_ifd_offset, unpack_short, unpack_long)
    focal_entry = exif_ifd.get(0x920A)
    if not focal_entry:
        return None
    value_type, count, value_offset = focal_entry
    if value_type == 5 and count == 1:
        return read_rational_as_int(payload, value_offset, unpack_long)
    if value_type in {3, 4} and count == 1:
        return int(value_offset)
    return None


def tiff_unpackers(payload: bytes):
    if len(payload) < 8:
        return None, None
    endian = payload[:2]
    if endian == b"II":
        prefix = "<"
    elif endian == b"MM":
        prefix = ">"
    else:
        return None, None

    def unpack_short(offset: int) -> int:
        if offset + 2 > len(payload):
            raise ValueError
        return struct.unpack_from(f"{prefix}H", payload, offset)[0]

    def unpack_long(offset: int) -> int:
        if offset + 4 > len(payload):
            raise ValueError
        return struct.unpack_from(f"{prefix}I", payload, offset)[0]

    return unpack_short, unpack_long


def read_tiff_ifd(payload: bytes, offset: int, unpack_short, unpack_long) -> dict[int, tuple[int, int, int]]:
    entries: dict[int, tuple[int, int, int]] = {}
    try:
        if offset < 0 or offset + 2 > len(payload):
            return entries
        count = unpack_short(offset)
        entry_offset = offset + 2
        for index in range(count):
            item_offset = entry_offset + index * 12
            if item_offset + 12 > len(payload):
                return entries
            tag = unpack_short(item_offset)
            value_type = unpack_short(item_offset + 2)
            item_count = unpack_long(item_offset + 4)
            value_offset = unpack_long(item_offset + 8)
            entries[tag] = (value_type, item_count, value_offset)
    except ValueError:
        return entries
    return entries


def read_rational_as_int(payload: bytes, offset: int, unpack_long) -> int | None:
    try:
        if offset < 0 or offset + 8 > len(payload):
            return None
        numerator = unpack_long(offset)
        denominator = unpack_long(offset + 4)
    except ValueError:
        return None
    if denominator == 0:
        return None
    return int(round(numerator / denominator))


def png_dimensions(header: bytes) -> tuple[int | None, int | None]:
    if len(header) < 24 or not header.startswith(b"\x89PNG\r\n\x1a\n"):
        return None, None
    if header[12:16] != b"IHDR":
        return None, None
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


def jpeg_dimensions(handle: BinaryIO) -> tuple[int | None, int | None]:
    metadata = parse_jpeg_metadata(handle)
    return metadata.width, metadata.height
