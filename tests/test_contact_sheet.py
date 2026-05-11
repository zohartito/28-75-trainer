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
        reviewed[0]["similarity_group"] = "sim-001"

        html = build_contact_sheet_html(reviewed, recommended_shots=[3], title="Selection <draft>")

        self.assertIn("Selection &lt;draft&gt;", html)
        self.assertIn("wide_&lt;unsafe&gt;.jpg", html)
        self.assertIn("Shot 3", html)
        self.assertIn("wide", html)
        self.assertIn("28mm", html)
        self.assertIn("horizontal", html)
        self.assertIn("Similarity Group", html)
        self.assertIn("Recommended", html)
        self.assertIn("Alternate", html)
        self.assertIn("ok", html)
        self.assertIn("soft_focus", html)
        self.assertIn("establishes &lt;context&gt;", html)
        self.assertNotIn("<unsafe>", html)
        self.assertNotIn("<context>", html)

    def test_build_contact_sheet_html_includes_decision_buckets_and_reason_sources(self) -> None:
        reviewed = [
            reviewed_item(3, "wide", filename="wide.jpg", source="/shoot/wide.jpg"),
            reviewed_item(9, "tight", filename="tight.jpg", source="/shoot/tight.jpg", status="warn"),
        ]

        html = build_contact_sheet_html(reviewed, recommended_shots=[3])

        self.assertIn("Decision Bucket", html)
        self.assertIn("Decision Reasons", html)
        self.assertIn("select", html)
        self.assertIn("practice-evidence", html)
        self.assertIn("deterministic:", html)
        self.assertIn("metadata:", html)

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

    def test_write_contact_sheet_refuses_to_overwrite_original_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "original.jpg"
            original.write_bytes(b"original bytes")

            with self.assertRaises(ValueError):
                write_contact_sheet_html(
                    [reviewed_item(1, "wide", source=str(original))],
                    original,
                    recommended_shots=[1],
                )

            self.assertEqual(original.read_bytes(), b"original bytes")

    def test_build_contact_sheet_preserves_top_level_decision_context(self) -> None:
        reviewed = {
            "schema_version": "0.1",
            "items": [reviewed_item(3, "wide", filename="wide.jpg", source="/shoot/wide.jpg")],
            "decision_overrides": {
                "3": {
                    "bucket": "reject",
                    "reason": "User rejected this frame after visual review.",
                }
            },
            "coach_preferences": {"3": ["Coach wants a different wide/context option."]},
        }

        html = build_contact_sheet_html(reviewed, recommended_shots=[3])

        self.assertIn("reject", html)
        self.assertIn("user_override:", html)
        self.assertIn("Coach wants a different wide/context option.", html)

    def test_build_contact_sheet_html_uses_local_preview_references_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "wide & safe local.jpg"
            local.write_bytes(b"local image bytes")
            reviewed = [
                reviewed_item(1, "wide", filename=local.name, source=str(local)),
                reviewed_item(2, "tight", source="https://example.com/remote.jpg"),
            ]

            html = build_contact_sheet_html(reviewed, recommended_shots=[1])

            self.assertIn("<th>Preview</th>", html)
            self.assertIn("<img", html)
            self.assertIn('loading="lazy"', html)
            self.assertIn("file:///", html)
            self.assertIn("No local preview", html)
            self.assertNotIn("https://example.com/remote.jpg", html)
            self.assertNotIn("wide & safe local.jpg", html)

    def test_write_contact_sheet_can_copy_preview_assets_without_touching_originals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shoot = root / "shoot"
            reports = root / "reports"
            assets = reports / "contact-assets"
            shoot.mkdir()
            reports.mkdir()
            original = shoot / "original.jpg"
            original.write_bytes(b"original preview bytes")
            before = original.read_bytes()

            output = reports / "contact-sheet.html"
            write_contact_sheet_html(
                [reviewed_item(1, "wide", source=str(original))],
                output,
                recommended_shots=[1],
                preview_assets_dir=assets,
            )

            generated = list(assets.iterdir())
            self.assertEqual(len(generated), 1)
            self.assertNotEqual(generated[0].resolve(), original.resolve())
            self.assertEqual(generated[0].read_bytes(), before)
            self.assertEqual(original.read_bytes(), before)
            html = output.read_text(encoding="utf-8")
            self.assertIn("contact-assets/shot-001-original.jpg", html)
            self.assertNotIn(str(original), html)

    def test_preview_asset_generation_refuses_to_write_inside_original_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shoot = root / "shoot"
            shoot.mkdir()
            original = shoot / "original.jpg"
            original.write_bytes(b"original bytes")

            with self.assertRaises(ValueError):
                write_contact_sheet_html(
                    [reviewed_item(1, "wide", source=str(original))],
                    root / "contact-sheet.html",
                    recommended_shots=[1],
                    preview_assets_dir=shoot / "contact-assets",
                )

            self.assertFalse((shoot / "contact-assets").exists())
            self.assertEqual(original.read_bytes(), b"original bytes")

    def test_similarity_group_column_is_only_rendered_when_available(self) -> None:
        without_similarity = build_contact_sheet_html([reviewed_item(1, "wide")], recommended_shots=[1])
        with_similarity = reviewed_item(1, "wide")
        with_similarity["similarity_group"] = "cluster <A>"

        html = build_contact_sheet_html([with_similarity], recommended_shots=[1])

        self.assertNotIn("Similarity Group", without_similarity)
        self.assertIn("Similarity Group", html)
        self.assertIn("cluster &lt;A&gt;", html)

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

    def test_contact_sheet_exposes_similarity_group_ids_and_repeated_group_sanity(self) -> None:
        reviewed = [
            reviewed_item(1, "wide", sha256="sha-a"),
            reviewed_item(2, "wide", sha256="sha-b"),
            reviewed_item(20, "wide", sha256="sha-c"),
        ]

        html = build_contact_sheet_html(reviewed, recommended_shots=[1, 2])
        sanity = visual_selection_sanity(reviewed, recommended_shots=[1, 2])

        self.assertIn("sim-001", html)
        self.assertFalse(sanity["ok"])
        self.assertIn("similarity_group_repeated", sanity["flags"])
        self.assertEqual(sanity["repeated_similarity_groups"], ["sim-001"])


def reviewed_item(
    shot: int,
    role: str,
    *,
    filename: str | None = None,
    source: str | None = None,
    status: str = "candidate",
    warnings: list[str] | None = None,
    notes: list[str] | None = None,
    sha256: str | None = None,
) -> dict:
    return {
        "trainer_shot": shot,
        "role": role,
        "source": source or f"/shoot/{shot:03d}.jpg",
        "sha256": sha256,
        "metadata": {
            "filename": filename or f"{shot:03d}.jpg",
            "focal_length": {"wide": 28, "massing": 35, "facade": 50, "tight": 75}.get(role),
            "orientation": "horizontal",
        },
        "image_analysis": {
            "tone": "balanced",
            "contrast": 150,
            "highlight_clip_pct": 0,
            "shadow_clip_pct": 0,
        },
        "status": status,
        "warnings": warnings or [],
        "notes": notes or [],
    }


if __name__ == "__main__":
    unittest.main()
