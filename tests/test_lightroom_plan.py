from __future__ import annotations

import csv
import io
import unittest

from trainer2875.lightroom_plan import lightroom_plan_to_csv, lightroom_plan_to_markdown


class LightroomPlanTests(unittest.TestCase):
    def test_exports_encode_markdown_and_neutralize_csv_formula_cells(self) -> None:
        handoff = adobe_mcp_handoff()
        photo = handoff["photos"][1]
        photo["filename"] = "[click](https://bad.example)"
        photo["photo_id"] = "=HYPERLINK(\"https://bad.example\")"
        photo["edit_intent"]["what_needs_fixing"] = ["<script>alert(1)</script>"]

        markdown = lightroom_plan_to_markdown(handoff, source_json_path="[source](bad)")
        rows = list(csv.DictReader(io.StringIO(lightroom_plan_to_csv(handoff))))

        self.assertIn("\\[click\\]\\(https://bad.example\\)", markdown)
        self.assertIn("\\<script\\>alert\\(1\\)\\</script\\>", markdown)
        self.assertEqual(rows[0]["photo_id"], "'=HYPERLINK(\"https://bad.example\")")

    def test_markdown_flattens_attacker_line_separators_and_block_openers(self) -> None:
        handoff = adobe_mcp_handoff()
        photo = handoff["photos"][1]
        photo["filename"] = "frame\r# forged heading\u2028> forged quote\n- forged list"
        photo["edit_intent"]["beginner_readable_explanation"] = "First line\n1. forged ordered item\x85[active](https://bad.example)"

        markdown = lightroom_plan_to_markdown(handoff)

        self.assertNotIn("\n# forged heading", markdown)
        self.assertNotIn("\n> forged quote", markdown)
        self.assertNotIn("\n- forged list", markdown)
        self.assertNotIn("\n1. forged ordered item", markdown)
        self.assertIn("frame \\# forged heading \\> forged quote - forged list", markdown)
        self.assertIn("First line 1. forged ordered item \\[active\\]\\(https://bad.example\\)", markdown)

    def test_markdown_export_groups_recommended_photos_with_boundary_language(self) -> None:
        handoff = adobe_mcp_handoff()

        markdown = lightroom_plan_to_markdown(handoff, source_json_path="reports/lightroom/source.json")

        self.assertIn("# Lightroom Classic Fix Sheet", markdown)
        self.assertIn("Source JSON: `reports/lightroom/source.json`", markdown)
        self.assertIn("Recommended set: 2, 5, 9", markdown)
        self.assertIn("planned-only", markdown)
        self.assertIn("No edits have been applied", markdown)
        self.assertIn("## Role: Wide Context", markdown)
        self.assertIn("## Role: Facade Detail Context", markdown)
        self.assertIn("## Role: Tight Detail Compression", markdown)
        self.assertLess(
            markdown.index("## Role: Wide Context"),
            markdown.index("## Role: Facade Detail Context"),
        )
        self.assertLess(
            markdown.index("## Role: Facade Detail Context"),
            markdown.index("## Role: Tight Detail Compression"),
        )
        self.assertIn("### Shot 2 - DSC00002.ARW", markdown)
        self.assertIn("Start by making the whole model read clearly.", markdown)
        self.assertIn("Enable lens profile corrections.", markdown)
        self.assertIn("Setting keys: `Exposure2012`, `Texture`", markdown)
        self.assertIn("### Shot 5 - DSC00005.ARW", markdown)
        self.assertIn("### Shot 9 - DSC00009.ARW", markdown)
        self.assertNotIn("DSC00001.ARW", markdown)

    def test_csv_export_has_required_fields_and_deterministic_setting_keys(self) -> None:
        handoff = adobe_mcp_handoff()

        csv_text = lightroom_plan_to_csv(handoff)
        rows = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertEqual(
            list(rows[0].keys()),
            ["photo_id", "trainer_shot", "filename", "role", "setting_keys", "status"],
        )
        self.assertEqual([row["trainer_shot"] for row in rows], ["2", "5", "9"])
        self.assertEqual([row["filename"] for row in rows], ["DSC00002.ARW", "DSC00005.ARW", "DSC00009.ARW"])
        self.assertEqual(rows[0]["role"], "wide_context")
        self.assertEqual(rows[0]["setting_keys"], "Exposure2012;Texture")
        self.assertEqual(rows[0]["status"], "planned")
        self.assertTrue(all(row["status"] == "planned" for row in rows))

    def test_review_like_dict_can_export_without_lightroom_handoff_wrapper(self) -> None:
        review = {
            "selection": {"recommended_set": [3]},
            "items": [
                {
                    "trainer_shot": 3,
                    "recommended": True,
                    "role": "massing_medium",
                    "filename": "DSC00003.ARW",
                    "status": "candidate",
                    "edit_intent": {
                        "status": "planned",
                        "beginner_readable_explanation": "Make the volume easy to understand.",
                        "what_needs_fixing": ["Straighten vertical edges."],
                        "develop_settings_planned": {"Texture": 12, "Contrast2012": 6},
                    },
                }
            ],
        }

        markdown = lightroom_plan_to_markdown(review, source_json_path="review.json")
        csv_text = lightroom_plan_to_csv(review)

        self.assertIn("Source JSON: `review.json`", markdown)
        self.assertIn("Recommended set: 3", markdown)
        self.assertIn("## Role: Massing Medium", markdown)
        self.assertIn("Make the volume easy to understand.", markdown)
        self.assertIn("Straighten vertical edges.", markdown)
        row = next(csv.DictReader(io.StringIO(csv_text)))
        self.assertEqual(row["photo_id"], "shot-003")
        self.assertEqual(row["setting_keys"], "Contrast2012;Texture")
        self.assertEqual(row["status"], "planned")


def adobe_mcp_handoff() -> dict:
    return {
        "handoff_type": "28-75_trainer_to_adobe_mcp",
        "status": "planned",
        "shoot": {"source_report_json": "reports/source-from-handoff.json"},
        "selection": {"recommended_set": [2, 5, 9]},
        "photos": [
            {
                "photo_id": "photo-001",
                "trainer_shot": 1,
                "recommended": False,
                "filename": "DSC00001.ARW",
                "role": "alternate",
                "status": "planned",
            },
            planned_photo(
                photo_id="photo-002",
                trainer_shot=2,
                filename="DSC00002.ARW",
                role="wide_context",
                beginner="Start by making the whole model read clearly.",
                fixes=["Enable lens profile corrections.", "Protect sunlit surfaces."],
                settings={"Texture": 8, "Exposure2012": 0.0},
            ),
            planned_photo(
                photo_id="photo-005",
                trainer_shot=5,
                filename="DSC00005.ARW",
                role="facade_detail_context",
                beginner="Keep the facade readable without losing context.",
                fixes=["Reduce highlights."],
                settings={"Clarity2012": 8},
            ),
            planned_photo(
                photo_id="photo-009",
                trainer_shot=9,
                filename="DSC00009.ARW",
                role="tight_detail_compression",
                beginner="Check this at 100 percent before sharpening.",
                fixes=["Verify focus at 100 percent."],
                settings={"Sharpness": 65},
            ),
        ],
    }


def planned_photo(
    *,
    photo_id: str,
    trainer_shot: int,
    filename: str,
    role: str,
    beginner: str,
    fixes: list[str],
    settings: dict[str, int | float],
) -> dict:
    return {
        "photo_id": photo_id,
        "trainer_shot": trainer_shot,
        "recommended": True,
        "filename": filename,
        "role": role,
        "status": "planned",
        "edit_intent": {
            "status": "planned",
            "beginner_readable_explanation": beginner,
            "what_needs_fixing": fixes,
            "develop_settings_planned": settings,
        },
    }


if __name__ == "__main__":
    unittest.main()
