from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from trainer2875.contact_sheet import (
    build_contact_sheet_html,
    visual_selection_sanity,
    write_contact_sheet_html,
)


class ContactSheetTests(unittest.TestCase):
    def test_build_contact_sheet_html_includes_review_fields_and_escapes_values(self) -> None:
        reviewed = [
            reviewed_item(
                3,
                "wide",
                filename="wide_<unsafe>.jpg",
                source="/shoot/wide_<unsafe>.jpg",
                status="ok",
                warnings=[],
                notes=["establishes <context>"],
            ),
            reviewed_item(
                9,
                "tight",
                filename="tight.jpg",
                source="/shoot/tight.jpg",
                status="warn",
                warnings=["soft_focus"],
                notes=["check at 100%"],
            ),
        ]

        html = build_contact_sheet_html(reviewed, recommended_shots=[3], title="Selection <draft>")

        self.assertIn("Selection &lt;draft&gt;", html)
        self.assertIn("wide_&lt;unsafe&gt;.jpg", html)
        self.assertIn("Shot 3", html)
        self.assertIn("wide", html)
        self.assertIn("Recommended", html)
        self.assertIn("Alternate", html)
        self.assertIn("ok", html)
        self.assertIn("soft_focus", html)
        self.assertIn("establishes &lt;context&gt;", html)
        self.assertNotIn("<unsafe>", html)
        self.assertNotIn("<context>", html)

    def test_write_contact_sheet_writes_only_the_explicit_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "original.jpg"
            output = root / "contact-sheet.html"
            original.write_bytes(b"original bytes")
            before = original.read_bytes()

            result = write_contact_sheet_html(
                [reviewed_item(1, "wide", source=str(original))],
                output,
                recommended_shots=[1],
            )

            self.assertEqual(result, output)
            self.assertTrue(output.exists())
            self.assertEqual(original.read_bytes(), before)

    def test_visual_selection_sanity_flags_narrow_shot_cluster_and_duplicate_sources(self) -> None:
        reviewed = [
            reviewed_item(1, "wide", filename="dup.jpg", source="/shoot/dup-a.jpg"),
            reviewed_item(2, "wide", filename="dup.jpg", source="/shoot/dup-b.jpg"),
            reviewed_item(3, "wide", filename="unique.jpg", source="/shoot/dup-a.jpg"),
            reviewed_item(40, "tight", filename="far.jpg", source="/shoot/far.jpg"),
        ]

        sanity = visual_selection_sanity(reviewed, recommended_shots=[1, 2, 3])

        self.assertFalse(sanity["ok"])
        self.assertIn("shot_cluster_too_narrow", sanity["flags"])
        self.assertIn("duplicate_filenames", sanity["flags"])
        self.assertIn("duplicate_source_paths", sanity["flags"])
        self.assertEqual(sanity["selected_shot_span"], 2)
        self.assertEqual(sanity["selected_count"], 3)

    def test_visual_selection_sanity_allows_spread_unique_selection(self) -> None:
        reviewed = [
            reviewed_item(1, "wide", filename="wide.jpg", source="/shoot/wide.jpg"),
            reviewed_item(20, "facade", filename="facade.jpg", source="/shoot/facade.jpg"),
            reviewed_item(40, "tight", filename="tight.jpg", source="/shoot/tight.jpg"),
        ]

        sanity = visual_selection_sanity(reviewed, recommended_shots=[1, 20, 40])

        self.assertTrue(sanity["ok"])
        self.assertEqual(sanity["flags"], [])


def reviewed_item(
    shot: int,
    role: str,
    *,
    filename: str | None = None,
    source: str | None = None,
    status: str = "candidate",
    warnings: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict:
    return {
        "trainer_shot": shot,
        "role": role,
        "source": source or f"/shoot/{shot:03d}.jpg",
        "metadata": {"filename": filename or f"{shot:03d}.jpg"},
        "status": status,
        "warnings": warnings or [],
        "notes": notes or [],
    }


if __name__ == "__main__":
    unittest.main()
