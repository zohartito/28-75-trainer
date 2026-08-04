from __future__ import annotations

import os
from pathlib import Path

from .metadata import exif_focal_length, infer_aperture, infer_focal_length, infer_iso, read_metadata  # noqa: F401
from .models import FolderAnalysis, PhotoAnalysis, SUPPORTED_IMAGE_EXTENSIONS
from .safeio import MAX_FILE_BYTES, MAX_FOLDER_BYTES, ReviewRoot, absolute_path, file_identity, hash_bounded, open_regular_file, verify_file_unchanged


def analyze_folder(folder: str | Path) -> FolderAnalysis:
    root = absolute_path(folder)
    if not root.exists():
        raise FileNotFoundError(f"Review folder does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Review target is not a folder: {root}")
    if root.is_symlink():
        raise ValueError(f"Review folder must not be a symlink: {root}")

    photos: list[PhotoAnalysis] = []
    unsupported: list[str] = []
    total_bytes = 0
    with ReviewRoot(root) as review_root:
        for entry in review_root.iter_entries():
            path = root / entry.relative
            relative = entry.relative.as_posix()
            if entry.is_symlink:
                unsupported.append(relative)
                continue
            suffix = path.suffix.lower()
            if suffix == ".xmp":
                continue
            if suffix not in SUPPORTED_IMAGE_EXTENSIONS:
                unsupported.append(relative)
                continue
            try:
                photo = analyze_photo(path, root, review_root)
            except (OSError, ValueError):
                photos.append(unreadable_photo(path, root))
                continue
            total_bytes += photo.bytes_size
            if total_bytes > MAX_FOLDER_BYTES:
                raise ValueError(f"Review folder exceeds the {MAX_FOLDER_BYTES} byte limit")
            photos.append(photo)
    return FolderAnalysis(root_name=root.name, photos=tuple(photos), unsupported_files=tuple(unsupported))


def analyze_photo(path: Path, root: Path, review_root: ReviewRoot | None = None) -> PhotoAnalysis:
    warnings: list[str] = []
    with open_regular_file(path, max_bytes=MAX_FILE_BYTES, root=review_root or root) as handle:
        file_stat = os.fstat(handle.fileno())
        identity = file_identity(handle)
        metadata = read_metadata(path, handle=handle, review_root=review_root or root)
        handle.seek(0)
        digest = sha256_handle(handle)
        verify_file_unchanged(handle, identity)
    warnings.extend(metadata.warnings)
    if metadata.width is None or metadata.height is None:
        warnings.append("dimensions_unavailable")
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            warnings.append("image_header_unreadable")
    if metadata.focal_length_mm is None:
        warnings.append("focal_length_unavailable")
    aperture = infer_aperture(path.name)
    iso = infer_iso(path.name)
    return PhotoAnalysis(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        extension=path.suffix.lower(),
        bytes_size=file_stat.st_size,
        sha256=digest,
        width=metadata.width,
        height=metadata.height,
        dimensions_source=metadata.dimensions_source,
        focal_length_mm=metadata.focal_length_mm,
        focal_length_source=metadata.focal_length_source,
        aperture=aperture,
        iso=iso,
        warnings=tuple(warnings),
    )


def unreadable_photo(path: Path, root: Path) -> PhotoAnalysis:
    """Keep a recognized but unreadable leaf local to one report row."""

    return PhotoAnalysis(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        extension=path.suffix.lower(),
        bytes_size=0,
        sha256="unavailable",
        focal_length_mm=None,
        focal_length_source="unavailable",
        warnings=("file_unreadable_or_limit_exceeded", "dimensions_unavailable", "focal_length_unavailable"),
    )


def sha256_file(path: Path) -> str:
    with open_regular_file(path, max_bytes=MAX_FILE_BYTES) as handle:
        return sha256_handle(handle)


def sha256_handle(handle) -> str:
    return hash_bounded(handle, max_bytes=MAX_FILE_BYTES)
