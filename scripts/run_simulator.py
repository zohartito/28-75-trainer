from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local 28-75 Trainer shoot simulations.")
    parser.add_argument("output", nargs="?", default="reports/simulator", help="Simulator output folder.")
    parser.add_argument("--keep", action="store_true", help="Keep any existing simulator output before adding files.")
    args = parser.parse_args()

    output = Path(args.output).expanduser()
    shoots = output / "shoots"
    reports = output / "reports"
    if output.exists() and not args.keep:
        shutil.rmtree(output)
    shoots.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    cases = [
        make_balanced_case(shoots / "balanced-field-map"),
        make_missing_metadata_case(shoots / "missing-metadata"),
        make_duplicate_case(shoots / "exact-duplicates"),
        make_unsupported_only_case(shoots / "unsupported-only"),
        make_corrupt_case(shoots / "corrupt-mixed"),
        make_nested_case(shoots / "nested-uppercase"),
    ]

    summaries = []
    for case in cases:
        html_path = reports / f"{case.name}.html"
        json_path = reports / f"{case.name}.json"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "trainer2875",
                "review",
                str(case),
                "--out",
                str(html_path),
                "--json-out",
                str(json_path),
            ],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        summary = {
            "case": case.name,
            "returncode": result.returncode,
            "html": html_path.as_posix(),
            "json": json_path.as_posix(),
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        if json_path.exists():
            data = json.loads(json_path.read_text(encoding="utf-8"))
            summary["score"] = data["scorecard"]["total_score"]
            summary["supported"] = len(data["analysis"]["photos"])
            summary["unsupported"] = len(data["analysis"]["unsupported_files"])
            summary["next_mission"] = data["next_mission"]["title"]
            summary["expectation_failures"] = expectation_failures(case.name, data)
        summaries.append(summary)

    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"Simulator output: {output}")
    for item in summaries:
        failures = item.get("expectation_failures", [])
        status = "OK" if item["returncode"] == 0 and not failures else "FAIL"
        score = item.get("score", "n/a")
        supported = item.get("supported", "n/a")
        unsupported = item.get("unsupported", "n/a")
        print(f"{status} {item['case']}: score={score}, supported={supported}, unsupported={unsupported}")
        for failure in failures:
            print(f"  - {failure}")
    print(f"Summary JSON: {summary_path}")
    return 0 if all(item["returncode"] == 0 and not item.get("expectation_failures") for item in summaries) else 1


def expectation_failures(case_name: str, data: dict) -> list[str]:
    score = data["scorecard"]["total_score"]
    supported = len(data["analysis"]["photos"])
    unsupported = len(data["analysis"]["unsupported_files"])
    duplicate_groups = data["scorecard"]["duplicate_groups"]
    failures: list[str] = []
    if case_name == "balanced-field-map":
        if score != 100:
            failures.append(f"expected perfect score 100, got {score}")
        if duplicate_groups:
            failures.append("expected no exact duplicate groups")
    elif case_name == "unsupported-only":
        if score != 0 or supported != 0 or unsupported == 0:
            failures.append("expected unsupported-only folder to score 0 with no recognized images")
    elif case_name == "exact-duplicates":
        if not duplicate_groups:
            failures.append("expected an exact duplicate group")
    elif case_name == "corrupt-mixed":
        warnings = {
            warning
            for photo in data["analysis"]["photos"]
            for warning in photo.get("warnings", [])
        }
        if "image_header_unreadable" not in warnings:
            failures.append("expected corrupt image to report image_header_unreadable")
    elif case_name == "nested-uppercase":
        if supported != 2 or unsupported != 1:
            failures.append("expected nested uppercase case to recognize 2 images and skip 1 unsupported file")
    return failures


def make_balanced_case(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for focal in (28, 35, 50, 75):
        write_png(folder / f"walk_{focal}mm_landscape.png", 1200, 800, tag=f"{focal}-landscape")
        write_png(folder / f"walk_{focal}mm_portrait.png", 800, 1200, tag=f"{focal}-portrait")
        write_jpeg_dimensions(folder / f"walk_{focal}mm_f4_iso400.JPG", 1600, 1000, tag=f"{focal}-jpeg")
    return folder


def make_missing_metadata_case(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(4):
        write_png(folder / f"frame_without_tags_{index}.png", 1000, 700)
    return folder


def make_duplicate_case(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / "detail_75mm_a.png"
    write_png(source, 900, 600)
    (folder / "detail_75mm_b.png").write_bytes(source.read_bytes())
    write_png(folder / "context_28mm.png", 1200, 800)
    return folder


def make_unsupported_only_case(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "notes.txt").write_text("Notes only.\n", encoding="utf-8")
    (folder / "sony_raw.ARW").write_bytes(b"not parsed in v0.1")
    return folder


def make_corrupt_case(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "broken_50mm.jpg").write_bytes(b"not a real jpeg")
    write_png(folder / "good_28mm.png", 1000, 700)
    return folder


def make_nested_case(folder: Path) -> Path:
    nested = folder / "day-one" / "selects"
    nested.mkdir(parents=True, exist_ok=True)
    write_jpeg_dimensions(nested / "STREET_35MM_F5.6_ISO800.JPG", 1800, 1200)
    write_png(nested / "street_75mm.png", 900, 1300)
    (folder / "readme.md").write_text("Nested test.\n", encoding="utf-8")
    return folder


def write_png(path: Path, width: int, height: int, tag: str = "") -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + (b"\x80\x80\x80" * width) for _ in range(height))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + (chunk(b"tEXt", tag.encode("utf-8")) if tag else b"")
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def write_jpeg_dimensions(path: Path, width: int, height: int, tag: str = "") -> None:
    sof = (
        b"\xff\xc0"
        + struct.pack(">H", 17)
        + b"\x08"
        + struct.pack(">HH", height, width)
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    )
    comment = b""
    if tag:
        data = tag.encode("utf-8")
        comment = b"\xff\xfe" + struct.pack(">H", len(data) + 2) + data
    path.write_bytes(b"\xff\xd8" + sof + comment + b"\xff\xd9")


if __name__ == "__main__":
    raise SystemExit(main())
