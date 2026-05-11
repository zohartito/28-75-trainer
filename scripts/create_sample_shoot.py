from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


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
    folder.mkdir(parents=True, exist_ok=True)
    for name, width, height in SAMPLES:
        write_png(folder / name, width, height)
    (folder / "notes.txt").write_text("Unsupported file used to verify skip behavior.\n", encoding="utf-8")
    print(f"Wrote sample shoot: {folder}")
    return 0


def write_png(path: Path, width: int, height: int) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + (b"\x80\x80\x80" * width) for _ in range(height))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


if __name__ == "__main__":
    raise SystemExit(main())
