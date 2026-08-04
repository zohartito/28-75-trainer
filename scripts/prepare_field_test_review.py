from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Keep this standalone helper executable from a source checkout as documented.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trainer2875.safeio import MAX_FILE_BYTES, MAX_FOLDER_BYTES, MAX_REVIEW_FILES, OutputDirectory, ReviewRoot, absolute_path, copy_bounded, open_regular_file, require_safe_component

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Copy field-test photos into a trainer review folder with filename focal-length tags. "
            "Original files are not modified. If there are more photos than one focal cycle, "
            "the focal-length block pattern repeats."
        )
    )
    parser.add_argument("source", help="Folder containing uploaded originals.")
    parser.add_argument("destination", help="Empty folder to receive tagged review copies.")
    parser.add_argument("--prefix", default="arch_model", help="Filename prefix for copied review images.")
    parser.add_argument(
        "--focals",
        default="28,35,50,75",
        help="Comma-separated focal lengths to assign in blocks. Default: 28,35,50,75.",
    )
    parser.add_argument(
        "--shots-per-focal",
        type=int,
        default=3,
        help="Number of sequential photos per focal length block. Default: 3.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        copied = prepare_review_folder(
            args.source,
            args.destination,
            prefix=args.prefix,
            focals=parse_focals(args.focals),
            shots_per_focal=args.shots_per_focal,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        parser.exit(status=2, message=f"error: {exc}\n")
    print(f"Copied {copied} image file(s) into {Path(args.destination)}")
    print("Next: run trainer2875 review on that destination folder.")
    return 0


def parse_focals(value: str) -> tuple[int, ...]:
    try:
        focals = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise ValueError("--focals must be a comma-separated list of numbers") from exc
    if not focals:
        raise ValueError("--focals must include at least one focal length")
    return focals


def prepare_review_folder(
    source: str | Path,
    destination: str | Path,
    *,
    prefix: str,
    focals: tuple[int, ...],
    shots_per_focal: int,
) -> int:
    if shots_per_focal < 1:
        raise ValueError("--shots-per-focal must be at least 1")
    source_path = absolute_path(source)
    destination_path = absolute_path(destination)
    require_safe_component(prefix, label="--prefix")
    if not source_path.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_path}")
    if not source_path.is_dir():
        raise NotADirectoryError(f"Source is not a folder: {source_path}")
    if source_path.is_symlink():
        raise ValueError("Source folder must not be a symlink")
    if destination_path.is_symlink():
        raise ValueError("Destination folder must not be a symlink")
    if destination_path.exists() and any(destination_path.iterdir()):
        raise ValueError(f"Destination must be empty: {destination_path}")
    destination_path.mkdir(parents=True, exist_ok=True)

    image_names: list[str] = []
    total_bytes = 0
    with ReviewRoot(source_path) as source_root:
        for entry in source_root.iter_entries():
            # Preserve the documented non-recursive source-folder contract,
            # while still counting/bounding nested directories and links.
            if len(entry.relative.parts) != 1:
                continue
            name = entry.relative.name
            if Path(name).suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                continue
            if entry.is_symlink:
                raise ValueError(f"Refusing symlinked source image: {name}")
            path = source_path / entry.relative
            with open_regular_file(path, max_bytes=MAX_FILE_BYTES, root=source_root) as handle:
                file_size = os.fstat(handle.fileno()).st_size
            total_bytes += file_size
            if len(image_names) >= MAX_REVIEW_FILES or total_bytes > MAX_FOLDER_BYTES:
                raise ValueError("Source review workload exceeds configured file or byte limits")
            image_names.append(name)
        if not image_names:
            raise ValueError(f"No supported image files found in: {source_path}")

        # Enumeration order is filesystem-dependent.  Make the focal cycle
        # reproducible only after validating and bounding every source leaf.
        image_names.sort(key=source_name_sort_key)

        with OutputDirectory(destination_path) as destination_root:
            for index, name in enumerate(image_names, start=1):
                source_file = source_path / name
                focal = focals[((index - 1) // shots_per_focal) % len(focals)]
                target_name = f"{prefix}_{focal}mm_{index:02d}{source_file.suffix.lower()}"
                copy_source_file(source_file, target_name, source_root=source_root, destination_root=destination_root)
    return len(image_names)


def source_name_sort_key(name: str) -> tuple[str, str]:
    """Provide a total, locale-independent order after source validation."""

    return (name.casefold(), name)


def copy_source_file(source: Path, destination_name: str, *, source_root: ReviewRoot, destination_root: OutputDirectory) -> None:
    """Copy from a no-follow source descriptor to an exclusive destination leaf."""

    try:
        with open_regular_file(source, max_bytes=MAX_FILE_BYTES, root=source_root) as reader, destination_root.open_exclusive(destination_name) as target:
            copy_bounded(reader, target, max_bytes=MAX_FILE_BYTES)
            target.flush()
            os.fsync(target.fileno())
    except Exception:
        try:
            destination_root.unlink(destination_name)
        except FileNotFoundError:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
