from __future__ import annotations

import argparse
import shutil
from pathlib import Path

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
    source_path = Path(source).expanduser().resolve()
    destination_path = Path(destination).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source folder does not exist: {source_path}")
    if not source_path.is_dir():
        raise NotADirectoryError(f"Source is not a folder: {source_path}")
    if destination_path.exists() and any(destination_path.iterdir()):
        raise ValueError(f"Destination must be empty: {destination_path}")
    destination_path.mkdir(parents=True, exist_ok=True)

    images = [
        path
        for path in sorted(source_path.iterdir(), key=lambda item: item.name.lower())
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    if not images:
        raise ValueError(f"No supported image files found in: {source_path}")

    for index, source_file in enumerate(images, start=1):
        focal = focals[((index - 1) // shots_per_focal) % len(focals)]
        target_name = f"{prefix}_{focal}mm_{index:02d}{source_file.suffix.lower()}"
        shutil.copy2(source_file, destination_path / target_name)
    return len(images)


if __name__ == "__main__":
    raise SystemExit(main())
