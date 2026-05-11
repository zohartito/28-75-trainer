from __future__ import annotations

import hashlib
from pathlib import Path

from .metadata import exif_focal_length, image_dimensions, infer_aperture, infer_focal_length, infer_iso, read_metadata
from .models import FolderAnalysis, PhotoAnalysis, SUPPORTED_IMAGE_EXTENSIONS


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
        if suffix == ".xmp" and is_supported_sidecar(path):
            continue
        if suffix not in SUPPORTED_IMAGE_EXTENSIONS:
            unsupported.append(relative)
            continue
        photos.append(analyze_photo(path, root))
    return FolderAnalysis(root_name=root.name, photos=tuple(photos), unsupported_files=tuple(unsupported))


def analyze_photo(path: Path, root: Path) -> PhotoAnalysis:
    stat = path.stat()
    warnings: list[str] = []
    metadata = read_metadata(path)
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
        bytes_size=stat.st_size,
        sha256=sha256_file(path),
        width=metadata.width,
        height=metadata.height,
        dimensions_source=metadata.dimensions_source,
        focal_length_mm=metadata.focal_length_mm,
        focal_length_source=metadata.focal_length_source,
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


def is_supported_sidecar(path: Path) -> bool:
    return any(
        sibling.is_file() and sibling.stem == path.stem and sibling.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        for sibling in path.parent.iterdir()
    )
