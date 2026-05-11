from __future__ import annotations

import re
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO


FOCAL_RE = re.compile(r"(?<!\d)(?P<focal>\d{2,3})\s?mm(?![A-Za-z0-9])", re.IGNORECASE)
APERTURE_RE = re.compile(r"(?<![A-Za-z0-9])f[_-]?(?P<aperture>\d+(?:[._]\d+)?)", re.IGNORECASE)
ISO_RE = re.compile(r"(?<![A-Za-z0-9])iso[_-]?(?P<iso>\d{2,6})(?![A-Za-z0-9])", re.IGNORECASE)
RAW_IMAGE_EXTENSIONS = {".arw", ".cr2", ".cr3", ".dng", ".nef", ".orf", ".raf", ".rw2", ".pef", ".srw"}


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


def read_metadata(path: Path) -> MetadataResult:
    suffix = path.suffix.lower()
    if suffix in RAW_IMAGE_EXTENSIONS:
        return raw_placeholder_metadata(path)

    width, height = image_dimensions(path)
    dimensions_source = "unavailable"
    if width is not None and height is not None:
        if suffix == ".png":
            dimensions_source = "png_header"
        elif suffix in {".jpg", ".jpeg"}:
            dimensions_source = "jpeg_header"
        else:
            dimensions_source = "image_header"

    focal_length = exif_focal_length(path)
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
    )


def raw_placeholder_metadata(path: Path) -> MetadataResult:
    sidecar = read_xmp_sidecar_metadata(path)
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
        warnings=("raw_image_not_decoded",),
    )


def read_xmp_sidecar_metadata(path: Path) -> XmpMetadata | None:
    sidecar = xmp_sidecar_path(path)
    if sidecar is None:
        return None
    try:
        tree = ET.parse(sidecar)
    except (OSError, ET.ParseError):
        return None
    fields: dict[str, str] = {}
    for element in tree.iter():
        for key, value in element.attrib.items():
            fields[local_name(key)] = value
        if element.text and element.text.strip():
            fields.setdefault(local_name(element.tag), element.text.strip())
    return XmpMetadata(
        width=parse_int(fields.get("PixelXDimension") or fields.get("ImageWidth") or fields.get("ExifImageWidth")),
        height=parse_int(fields.get("PixelYDimension") or fields.get("ImageLength") or fields.get("ExifImageHeight")),
        focal_length_mm=parse_focal_value(fields.get("FocalLength")),
    )


def xmp_sidecar_path(path: Path) -> Path | None:
    for suffix in (".xmp", ".XMP"):
        candidate = path.with_suffix(suffix)
        if candidate.is_file():
            return candidate
    return None


def local_name(name: str) -> str:
    if "}" in name:
        return name.rsplit("}", 1)[1]
    return name.rsplit(":", 1)[-1]


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\d+", value)
    if not match:
        return None
    return int(match.group(0))


def parse_focal_value(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip()
    rational = re.fullmatch(r"(?P<numerator>\d+(?:\.\d+)?)/(?P<denominator>\d+(?:\.\d+)?)", text)
    if rational:
        denominator = float(rational.group("denominator"))
        if denominator == 0:
            return None
        return int(round(float(rational.group("numerator")) / denominator))
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    return int(round(float(match.group(0))))


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


def image_dimensions(path: Path) -> tuple[int | None, int | None]:
    suffix = path.suffix.lower()
    try:
        with path.open("rb") as handle:
            if suffix == ".png":
                return png_dimensions(handle.read(32))
            if suffix in {".jpg", ".jpeg"}:
                return jpeg_dimensions(handle)
    except OSError:
        return None, None
    return None, None


def exif_focal_length(path: Path) -> int | None:
    if path.suffix.lower() not in {".jpg", ".jpeg"}:
        return None
    try:
        with path.open("rb") as handle:
            payload = jpeg_exif_payload(handle)
    except OSError:
        return None
    if payload is None:
        return None
    return tiff_focal_length(payload)


def jpeg_exif_payload(handle: BinaryIO) -> bytes | None:
    if handle.read(2) != b"\xff\xd8":
        return None
    while True:
        marker_prefix = handle.read(1)
        if marker_prefix == b"":
            return None
        if marker_prefix != b"\xff":
            continue
        marker = handle.read(1)
        while marker == b"\xff":
            marker = handle.read(1)
        if marker in {b"\xd8", b"\xd9"}:
            continue
        length_bytes = handle.read(2)
        if len(length_bytes) != 2:
            return None
        segment_length = struct.unpack(">H", length_bytes)[0]
        if segment_length < 2:
            return None
        payload = handle.read(segment_length - 2)
        if marker == b"\xe1" and payload.startswith(b"Exif\x00\x00"):
            return payload[6:]


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
    if handle.read(2) != b"\xff\xd8":
        return None, None
    while True:
        marker_prefix = handle.read(1)
        if marker_prefix == b"":
            return None, None
        if marker_prefix != b"\xff":
            continue
        marker = handle.read(1)
        while marker == b"\xff":
            marker = handle.read(1)
        if marker in {b"\xd8", b"\xd9"}:
            continue
        length_bytes = handle.read(2)
        if len(length_bytes) != 2:
            return None, None
        segment_length = struct.unpack(">H", length_bytes)[0]
        if segment_length < 2:
            return None, None
        if marker and marker[0] in {
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
        }:
            data = handle.read(5)
            if len(data) != 5:
                return None, None
            height, width = struct.unpack(">HH", data[1:5])
            return int(width), int(height)
        handle.seek(segment_length - 2, 1)
