from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path
from typing import BinaryIO

from .models import FolderAnalysis, PhotoAnalysis, SUPPORTED_IMAGE_EXTENSIONS

FOCAL_RE = re.compile(r"(?<!\d)(?P<focal>\d{2,3})\s?mm(?![A-Za-z0-9])", re.IGNORECASE)
APERTURE_RE = re.compile(r"(?<![A-Za-z0-9])f[_-]?(?P<aperture>\d+(?:[._]\d+)?)", re.IGNORECASE)
ISO_RE = re.compile(r"(?<![A-Za-z0-9])iso[_-]?(?P<iso>\d{2,6})(?![A-Za-z0-9])", re.IGNORECASE)


def analyze_folder(folder: str | Path) -> FolderAnalysis:
    root = Path(folder).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Review folder does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Review target is not a folder: {root}")

    photos: list[PhotoAnalysis] = []
    unsupported: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            unsupported.append(relative)
            continue
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_IMAGE_EXTENSIONS:
            unsupported.append(relative)
            continue
        photos.append(analyze_photo(path, root))
    return FolderAnalysis(root_name=root.name, photos=tuple(photos), unsupported_files=tuple(unsupported))


def analyze_photo(path: Path, root: Path) -> PhotoAnalysis:
    stat = path.stat()
    warnings: list[str] = []
    width, height = image_dimensions(path)
    if width is None or height is None:
        warnings.append("dimensions_unavailable")
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            warnings.append("image_header_unreadable")
    focal_length = exif_focal_length(path) or infer_focal_length(path.name)
    if focal_length is None:
        warnings.append("focal_length_unavailable")
    aperture = infer_aperture(path.name)
    iso = infer_iso(path.name)
    return PhotoAnalysis(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        extension=path.suffix.lower(),
        bytes_size=stat.st_size,
        sha256=sha256_file(path),
        width=width,
        height=height,
        focal_length_mm=focal_length,
        aperture=aperture,
        iso=iso,
        warnings=tuple(warnings),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def jpeg_dimensions(handle) -> tuple[int | None, int | None]:
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
