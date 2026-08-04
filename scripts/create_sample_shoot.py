from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trainer2875.safeio import OutputDirectory, atomic_write_bytes, require_safe_component


SAMPLES = (
    ("street_28mm_landscape.png", 1200, 800),
    ("street_35mm_portrait.png", 800, 1200),
    ("street_50mm_square.png", 900, 900),
    ("street_75mm_detail.png", 1000, 700),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a tiny synthetic sample shoot for 28-75 Trainer.")
    parser.add_argument("folder", help="Destination folder.")
    args = parser.parse_args()
    folder = Path(args.folder).expanduser()
    if folder.is_symlink():
        parser.error("Destination folder must not be a symlink.")
    folder.mkdir(parents=True, exist_ok=True)
    if folder.is_symlink():
        parser.error("Destination folder must not be a symlink.")
    generate_sample_shoot(folder)
    print(f"Wrote sample shoot: {folder}")
    return 0


def write_png(path: Path, width: int, height: int) -> None:
    atomic_write_bytes(path, png_bytes(width, height))


def png_bytes(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + (b"\x80\x80\x80" * width) for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def generate_sample_shoot(folder: Path, *, after_first_write: Callable[[], None] | None = None) -> None:
    """Write every generated leaf through one retained destination descriptor."""

    with OutputDirectory(folder) as destination:
        for index, (name, width, height) in enumerate(SAMPLES):
            require_safe_component(name, label="sample filename")
            destination.atomic_write_bytes(name, png_bytes(width, height))
            if index == 0 and after_first_write is not None:
                after_first_write()
        destination.atomic_write_text("notes.txt", "Unsupported file used to verify skip behavior.\n")


if __name__ == "__main__":
    raise SystemExit(main())
