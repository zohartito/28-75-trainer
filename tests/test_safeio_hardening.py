from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.create_sample_shoot import SAMPLES, generate_sample_shoot
from trainer2875.field_review import image_quality_score
from trainer2875.lightroom_plan import lightroom_plan_to_markdown
from trainer2875.reporting import finite_number
from trainer2875.safeio import OutputTarget, ReviewRoot, copy_bounded, hash_bounded


class DescriptorBoundaryTests(unittest.TestCase):
    def test_append_retains_parent_and_preserves_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "state"
            parent.mkdir()
            external = root / "external"
            external.mkdir()
            (external / "log.md").write_text("untouched", encoding="utf-8")
            with OutputTarget(parent / "log.md") as target:
                moved = root / "retained"
                parent.rename(moved)
                parent.symlink_to(external, target_is_directory=True)
                target.append_text("first\n", initial="header\n")
                target.append_text("second\n", initial="header\n")
            self.assertEqual((moved / "log.md").read_text(), "header\nfirst\nsecond\n")
            self.assertEqual((external / "log.md").read_text(), "untouched")

    def test_output_parent_swap_cannot_redirect_retained_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "reports"
            parent.mkdir()
            external = root / "external"
            external.mkdir()
            output = parent / "review.html"
            with OutputTarget(output) as target:
                moved = root / "reports-moved"
                parent.rename(moved)
                parent.symlink_to(external, target_is_directory=True)
                target.write_text("trusted output")

            self.assertEqual((moved / "review.html").read_text(encoding="utf-8"), "trusted output")
            self.assertFalse((external / "review.html").exists())

    def test_review_root_retains_descriptor_across_parent_swap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reviewed = root / "reviewed"
            reviewed.mkdir()
            (reviewed / "frame.jpg").write_bytes(b"reviewed")
            external = root / "external"
            external.mkdir()
            (external / "frame.jpg").write_bytes(b"external")
            with ReviewRoot(reviewed) as review_root:
                moved = root / "reviewed-moved"
                reviewed.rename(moved)
                reviewed.symlink_to(external, target_is_directory=True)
                with review_root.open_regular(reviewed / "frame.jpg", max_bytes=100) as handle:
                    self.assertEqual(handle.read(), b"reviewed")

    def test_streaming_enumeration_bounds_directories_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested").mkdir()
            (root / "nested" / "frame.jpg").write_bytes(b"x")
            link = root / "link"
            try:
                link.symlink_to(root / "nested", target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable on this platform: {exc}")
            with ReviewRoot(root) as review_root:
                with self.assertRaisesRegex(ValueError, "entry limit"):
                    list(review_root.iter_entries(max_entries=2))

    def test_growing_hash_and_copy_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "source.bin"
            source_path.write_bytes(b"before")
            destination_path = Path(tmp) / "destination.bin"

            with source_path.open("rb") as source:
                growing = GrowingReader(source, source_path)
                with self.assertRaisesRegex(ValueError, "changed"):
                    hash_bounded(growing, max_bytes=100)

            source_path.write_bytes(b"before")
            with source_path.open("rb") as source, destination_path.open("wb") as destination:
                growing = GrowingReader(source, source_path)
                with self.assertRaisesRegex(ValueError, "changed"):
                    copy_bounded(growing, destination, max_bytes=100)


class InputAndMarkupHardeningTests(unittest.TestCase):
    def test_commonmark_code_span_cannot_close_into_active_link(self) -> None:
        source = "` [active](https://example.invalid) `"
        markdown = lightroom_plan_to_markdown({"items": []}, source_json_path=source)
        self.assertIn("Source JSON: `` ` [active](https://example.invalid) ` ``", markdown)
        self.assertNotIn("Source JSON: `[active]", markdown)

    def test_out_of_range_ranking_inputs_and_huge_integers_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "contrast"):
            image_quality_score({"image_analysis": {"contrast": 256}})
        with self.assertRaisesRegex(ValueError, "clip"):
            image_quality_score({"image_analysis": {"highlight_clip_pct": -1}})
        self.assertFalse(finite_number(10**10_000))

    def test_sample_generator_replaces_symlink_leaf_not_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "sample"
            folder.mkdir()
            protected = root / "protected.png"
            protected.write_bytes(b"keep")
            try:
                (folder / "street_28mm_landscape.png").symlink_to(protected)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable on this platform: {exc}")
            result = subprocess.run(
                [sys.executable, "scripts/create_sample_shoot.py", str(folder)],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(protected.read_bytes(), b"keep")
            self.assertFalse((folder / "street_28mm_landscape.png").is_symlink())

    def test_sample_generator_keeps_one_destination_after_directory_swap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "sample"
            folder.mkdir()
            external = root / "external"
            external.mkdir()
            protected = root / "protected.png"
            protected.write_bytes(b"keep")
            try:
                (folder / SAMPLES[0][0]).symlink_to(protected)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable on this platform: {exc}")

            def swap_directory() -> None:
                moved = root / "sample-retained"
                folder.rename(moved)
                folder.symlink_to(external, target_is_directory=True)

            generate_sample_shoot(folder, after_first_write=swap_directory)

            moved = root / "sample-retained"
            self.assertEqual(protected.read_bytes(), b"keep")
            self.assertEqual(sorted(path.name for path in moved.iterdir()), sorted([name for name, _, _ in SAMPLES] + ["notes.txt"]))
            self.assertEqual(list(external.iterdir()), [])

    def test_workflow_yaml_files_parse_with_ruby_psych(self) -> None:
        for workflow in sorted((Path(__file__).resolve().parents[1] / ".github" / "workflows").glob("*.yml")):
            result = subprocess.run(
                ["ruby", "-e", "require 'yaml'; YAML.safe_load(File.read(ARGV.fetch(0)), aliases: false)", str(workflow)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


class GrowingReader:
    def __init__(self, wrapped, path: Path):
        self.wrapped = wrapped
        self.path = path
        self.grown = False

    def fileno(self) -> int:
        return self.wrapped.fileno()

    def read(self, size: int = -1) -> bytes:
        data = self.wrapped.read(size)
        if data and not self.grown:
            self.grown = True
            with self.path.open("ab") as writer:
                writer.write(b"after")
        return data


if __name__ == "__main__":
    unittest.main()
