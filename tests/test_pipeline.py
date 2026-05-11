from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

from trainer2875.analysis import analyze_folder, exif_focal_length, infer_aperture, infer_focal_length, infer_iso
from trainer2875.coaching import build_coaching_report
from trainer2875.mission import DEFAULT_MISSION, mission_for_focus, mission_to_markdown
from trainer2875.reporting import (
    load_report_json,
    report_to_html,
    validate_distinct_output_paths,
    validate_report_regeneration_paths,
    validate_review_output_locations,
    write_text_output,
)


class PipelineTests(unittest.TestCase):
    def test_filename_metadata_inference(self) -> None:
        filename = "walk_75mm_f2.8_iso400_001.jpg"
        self.assertEqual(infer_focal_length(filename), 75)
        self.assertEqual(infer_aperture(filename), "f/2.8")
        self.assertEqual(infer_iso(filename), 400)

    def test_jpeg_exif_focal_length_is_used_when_filename_has_no_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "DSC0001.jpg"
            write_jpeg_with_exif_focal_length(image, 75, 1600, 1000)
            analysis = analyze_folder(root)
            self.assertEqual(exif_focal_length(image), 75)
            self.assertEqual(analysis.photos[0].focal_length_mm, 75)
            self.assertEqual(analysis.photos[0].width, 1600)
            self.assertEqual(analysis.photos[0].height, 1000)

    def test_mission_markdown_has_training_constraints(self) -> None:
        markdown = mission_to_markdown(DEFAULT_MISSION)
        self.assertIn("28-75 Field Map", markdown)
        self.assertIn("Minimum shots: 12", markdown)
        self.assertIn("28mm, 35mm, 50mm, 75mm", markdown)

    def test_review_pipeline_scores_and_keeps_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_png(root / "frame_28mm_landscape.png", 1200, 800)
            write_png(root / "frame_35mm_portrait.png", 800, 1200)
            write_png(root / "frame_50mm_square.png", 900, 900)
            duplicate_source = root / "frame_75mm_a.png"
            duplicate_copy = root / "frame_75mm_b.png"
            write_png(duplicate_source, 1000, 700)
            duplicate_copy.write_bytes(duplicate_source.read_bytes())
            (root / "notes.txt").write_text("not an image", encoding="utf-8")

            before = {path.name: path.read_bytes() for path in root.glob("*.png")}
            analysis = analyze_folder(root)
            report = build_coaching_report(analysis, DEFAULT_MISSION)
            after = {path.name: path.read_bytes() for path in root.glob("*.png")}

            self.assertEqual(before, after)
            self.assertEqual(len(analysis.photos), 5)
            self.assertEqual(analysis.unsupported_files, ("notes.txt",))
            self.assertEqual(report.scorecard.component_scores["focal_coverage"], 100)
            self.assertTrue(report.scorecard.duplicate_groups)
            self.assertIn("Next Mission", report_to_html(report))

    def test_empty_folder_does_not_get_free_selection_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            analysis = analyze_folder(tmp)
            report = build_coaching_report(analysis, DEFAULT_MISSION)
            self.assertEqual(report.scorecard.component_scores["selection_discipline"], 0)
            self.assertEqual(report.scorecard.total_score, 0)
            self.assertIn("not enough evidence", " ".join(report.scorecard.observations))

    def test_corrupt_jpeg_does_not_earn_focal_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad_75mm.jpg").write_bytes(b"not a real jpeg")
            analysis = analyze_folder(root)
            report = build_coaching_report(analysis, mission_for_focus("75mm"))
            self.assertEqual(len(analysis.photos), 1)
            self.assertIn("image_header_unreadable", analysis.photos[0].warnings)
            self.assertEqual(report.scorecard.component_scores["focal_coverage"], 0)

    def test_report_output_rejects_image_like_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for suffix in (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"):
                with self.subTest(suffix=suffix):
                    with self.assertRaises(ValueError):
                        write_text_output(Path(tmp) / f"original{suffix}", "not allowed")

    def test_output_paths_must_be_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            same = Path(tmp) / "review.html"
            with self.assertRaises(ValueError):
                validate_distinct_output_paths(same, same)

    def test_output_path_rejects_existing_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "original.jpg"
            target.write_bytes(b"original")
            output = root / "review.html"
            try:
                output.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable on this platform: {exc}")
            with self.assertRaises(ValueError):
                write_text_output(output, "not allowed")
            self.assertEqual(target.read_bytes(), b"original")

    def test_output_path_rejects_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "external"
            external.mkdir()
            linked_parent = root / "reports-link"
            try:
                linked_parent.symlink_to(external, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable on this platform: {exc}")
            with self.assertRaises(ValueError):
                write_text_output(linked_parent / "review.html", "not allowed")
            self.assertFalse((external / "review.html").exists())

    def test_report_regeneration_refuses_to_overwrite_json_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            same = Path(tmp) / "review.json"
            same.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_report_regeneration_paths(same, same)

    def test_coaching_language_does_not_overclaim_visual_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_png(root / "frame_28mm_landscape.png", 1200, 800)
            report = build_coaching_report(analyze_folder(root), DEFAULT_MISSION)
            combined = " ".join(report.recommendations) + " " + report.next_mission.objective
            self.assertNotIn("strong horizontal composition", combined)
            self.assertNotIn("strong vertical", combined)
            self.assertNotIn("deserves to exist", combined)

    def test_duplicate_language_is_exact_hash_based(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "frame_75mm_a.png"
            write_png(source, 900, 600)
            (root / "frame_75mm_b.png").write_bytes(source.read_bytes())
            report = build_coaching_report(analyze_folder(root), mission_for_focus("75mm"))
            combined = " ".join(report.scorecard.observations + report.recommendations)
            self.assertIn("byte-identical", combined)
            self.assertIn("SHA-256", combined)
            self.assertIn("does not compare near-duplicates", combined.lower())

    def test_focus_missions_do_not_claim_exif_capture_verification(self) -> None:
        wide = mission_to_markdown(mission_for_focus("wide"))
        tele = mission_to_markdown(mission_for_focus("75mm"))
        self.assertNotIn("captured near", wide)
        self.assertNotIn("captured near", tele)
        self.assertIn("filename-tagged", wide)
        self.assertIn("filename-tagged", tele)

    def test_review_outputs_are_refused_inside_reviewed_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shoot = Path(tmp) / "shoot"
            shoot.mkdir()
            with self.assertRaises(ValueError):
                validate_review_output_locations(shoot, shoot / "review.html", Path(tmp) / "review.json")

    def test_scan_skips_symlinked_image_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root.parent / "external_28mm.png"
            write_png(external, 400, 300)
            link = root / "linked_28mm.png"
            try:
                link.symlink_to(external)
            except OSError as exc:
                external.unlink(missing_ok=True)
                self.skipTest(f"symlinks unavailable on this platform: {exc}")
            try:
                analysis = analyze_folder(root)
                self.assertEqual(len(analysis.photos), 0)
                self.assertEqual(analysis.unsupported_files, ("linked_28mm.png",))
            finally:
                external.unlink(missing_ok=True)

    def test_html_report_escapes_loaded_json_values(self) -> None:
        data = {
            "schema_version": "1.0",
            "mission": {
                "title": "<script>alert(1)</script>",
                "objective": "Use <wide> framing.",
            },
            "scorecard": {
                "total_score": "<img src=x onerror=alert(1)>",
                "component_scores": {"volume": "<b>bad</b>"},
                "observations": ["Observed <unsafe> value."],
                "duplicate_groups": [["a<script>.jpg", "b.png"]],
            },
            "analysis": {
                "photos": [
                    {
                        "relative_path": "frame_<bad>.png",
                        "focal_length_mm": 28,
                        "width": 100,
                        "height": 50,
                        "orientation": "landscape",
                        "megapixels": 0.01,
                        "warnings": ["warn_<x>"],
                    }
                ],
                "unsupported_files": ["notes_<bad>.txt"],
            },
            "recommendations": ["Try <again>."],
            "next_mission": {
                "title": "Next <mission>",
                "objective": "Keep <originals> safe.",
            },
        }
        html = report_to_html(data)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("Score &lt;img src=x onerror=alert(1)&gt;/100", html)
        self.assertIn("frame_&lt;bad&gt;.png", html)
        self.assertIn("Coach Read", html)
        self.assertIn("This report does not judge sharpness", html)
        self.assertIn("Filename Focal Tag", html)
        self.assertIn("Exact File Duplicate Groups", html)

    def test_loaded_report_json_requires_schema_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps({"mission": {}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_report_json(bad)

    def test_loaded_report_json_rejects_unknown_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(
                json.dumps(
                    {
                        "schema_version": "99.0",
                        "mission": {"title": "Old", "objective": "Old shape."},
                        "analysis": {"photos": [], "unsupported_files": []},
                        "scorecard": {
                            "total_score": 0,
                            "component_scores": {},
                            "observations": [],
                            "duplicate_groups": [],
                        },
                        "recommendations": [],
                        "next_mission": {"title": "Next", "objective": "Next."},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_report_json(bad)

    def test_cli_report_bad_json_shape_exits_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            out = Path(tmp) / "out.html"
            bad.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "trainer2875",
                    "report",
                    str(bad),
                    "--out",
                    str(out),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(out.exists())
            self.assertIn("missing required field", result.stderr)

    def test_cli_mission_review_report_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shoot = work / "shoot"
            shoot.mkdir()
            write_png(shoot / "street_28mm.png", 1200, 800)
            write_png(shoot / "street_75mm.png", 800, 1200)
            mission_path = work / "mission.md"
            html_path = work / "review.html"
            json_path = work / "review.json"
            html_copy = work / "review-copy.html"

            self.run_cli("mission", "--out", str(mission_path))
            self.run_cli("review", str(shoot), "--out", str(html_path), "--json-out", str(json_path), "--json")
            self.run_cli("report", str(json_path), "--out", str(html_copy))

            self.assertTrue(mission_path.exists())
            self.assertTrue(html_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(html_copy.exists())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0")
            self.assertEqual(data["analysis"]["root_name"], "shoot")
            self.assertIn("next_mission", data)

    def test_cli_review_refuses_same_output_path_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shoot = work / "shoot"
            shoot.mkdir()
            write_png(shoot / "street_28mm.png", 1200, 800)
            same = work / "review.html"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "trainer2875",
                    "review",
                    str(shoot),
                    "--out",
                    str(same),
                    "--json-out",
                    str(same),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(same.exists())
            self.assertIn("same path", result.stderr)

    def test_cli_report_refuses_same_input_and_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "review.json"
            report.write_text("{}", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "trainer2875",
                    "report",
                    str(report),
                    "--out",
                    str(report),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report.read_text(encoding="utf-8"), "{}")
            self.assertIn("overwrite the JSON report", result.stderr)

    def test_cli_review_preflights_both_output_paths_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shoot = work / "shoot"
            shoot.mkdir()
            write_png(shoot / "street_28mm.png", 1200, 800)
            html_path = work / "review.html"
            bad_json_path = work / "original.jpg"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "trainer2875",
                    "review",
                    str(shoot),
                    "--out",
                    str(html_path),
                    "--json-out",
                    str(bad_json_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(html_path.exists())
            self.assertFalse(bad_json_path.exists())
            self.assertIn("image-like path", result.stderr)

    def test_cli_review_refuses_outputs_inside_reviewed_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shoot = work / "shoot"
            shoot.mkdir()
            write_png(shoot / "street_28mm.png", 1200, 800)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "trainer2875",
                    "review",
                    str(shoot),
                    "--out",
                    str(shoot / "review.html"),
                    "--json-out",
                    str(work / "review.json"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse((shoot / "review.html").exists())
            self.assertFalse((work / "review.json").exists())
            self.assertIn("inside the reviewed folder", result.stderr)

    def test_prepare_field_test_review_copies_tagged_files_without_touching_originals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            source = work / "originals"
            destination = work / "review-copy"
            source.mkdir()
            for index in range(1, 5):
                write_png(source / f"DSC_{index:04d}.PNG", 100 + index, 80 + index)
            before = {path.name: path.read_bytes() for path in source.iterdir()}

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/prepare_field_test_review.py",
                    str(source),
                    str(destination),
                    "--prefix",
                    "model",
                    "--focals",
                    "28,75",
                    "--shots-per-focal",
                    "1",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=True,
            )

            after = {path.name: path.read_bytes() for path in source.iterdir()}
            self.assertEqual(before, after)
            self.assertIn("Copied 4 image file", result.stdout)
            self.assertEqual(
                [path.name for path in sorted(destination.iterdir())],
                [
                    "model_28mm_01.png",
                    "model_28mm_03.png",
                    "model_75mm_02.png",
                    "model_75mm_04.png",
                ],
            )

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "trainer2875", *args],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=True,
        )


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


def write_jpeg_with_exif_focal_length(path: Path, focal_length: int, width: int, height: int) -> None:
    tiff = build_exif_tiff_payload(focal_length)
    app1_payload = b"Exif\x00\x00" + tiff
    app1 = b"\xff\xe1" + struct.pack(">H", len(app1_payload) + 2) + app1_payload
    sof_payload = (
        b"\x08"
        + struct.pack(">HH", height, width)
        + b"\x03"
        + b"\x01\x11\x00"
        + b"\x02\x11\x00"
        + b"\x03\x11\x00"
    )
    sof = b"\xff\xc0" + struct.pack(">H", len(sof_payload) + 2) + sof_payload
    path.write_bytes(b"\xff\xd8" + app1 + sof + b"\xff\xd9")


def build_exif_tiff_payload(focal_length: int) -> bytes:
    exif_ifd_offset = 26
    rational_offset = 44
    return (
        b"II"
        + struct.pack("<H", 42)
        + struct.pack("<I", 8)
        + struct.pack("<H", 1)
        + struct.pack("<HHII", 0x8769, 4, 1, exif_ifd_offset)
        + struct.pack("<I", 0)
        + struct.pack("<H", 1)
        + struct.pack("<HHII", 0x920A, 5, 1, rational_offset)
        + struct.pack("<I", 0)
        + struct.pack("<II", focal_length, 1)
    )


if __name__ == "__main__":
    unittest.main()
