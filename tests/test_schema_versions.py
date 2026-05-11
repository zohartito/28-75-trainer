from __future__ import annotations

import copy
import csv
import io
import tempfile
import unittest
from pathlib import Path

from trainer2875.adobe_mcp import dry_run_adobe_mcp_handoff
from trainer2875.contact_sheet import build_contact_sheet_html, visual_selection_sanity
from trainer2875.field_review import build_adobe_mcp_handoff
from trainer2875.field_review_cli import load_field_review_json, validate_field_review_data
from trainer2875.lightroom_plan import lightroom_plan_to_csv, lightroom_plan_to_markdown
from trainer2875.reporting import validate_report_data
from trainer2875.schema_versions import (
    ADOBE_MCP_HANDOFF_SCHEMA_VERSION,
    CONTACT_SHEET_SCHEMA_VERSION,
    FIELD_REVIEW_SCHEMA_VERSION,
    LIGHTROOM_PLAN_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
)


class SchemaVersionTests(unittest.TestCase):
    def test_report_accepts_current_version_and_old_v0_1_shape(self) -> None:
        data = old_v0_1_report_shape()

        validate_report_data(data)

    def test_report_rejects_unsupported_future_version(self) -> None:
        data = old_v0_1_report_shape()
        data["schema_version"] = "99.0"

        with self.assertRaisesRegex(ValueError, "Unsupported report schema version"):
            validate_report_data(data)

    def test_adobe_mcp_handoff_accepts_current_version(self) -> None:
        handoff = sample_handoff()

        result = dry_run_adobe_mcp_handoff(handoff)

        self.assertTrue(result["ok"])
        self.assertEqual(handoff["schema_version"], ADOBE_MCP_HANDOFF_SCHEMA_VERSION)

    def test_adobe_mcp_handoff_rejects_unsupported_future_version(self) -> None:
        handoff = sample_handoff()
        handoff["schema_version"] = "99.0"

        result = dry_run_adobe_mcp_handoff(handoff)

        self.assertFalse(result["ok"])
        self.assertIn("unsupported_schema_version", issue_codes(result["errors"]))

    def test_field_review_json_accepts_current_version_and_legacy_missing_version(self) -> None:
        current = {"schema_version": FIELD_REVIEW_SCHEMA_VERSION, "items": [review_item(1)]}
        legacy = {"items": [review_item(2)]}

        validate_field_review_data(current)
        validate_field_review_data(legacy)

    def test_field_review_json_rejects_unsupported_future_version_when_present(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported field review schema version"):
            validate_field_review_data({"schema_version": "99.0", "items": []})

    def test_load_field_review_json_validates_version_from_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "field-review.json"
            path.write_text('{"schema_version": "99.0", "items": []}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported field review schema version"):
                load_field_review_json(path)

    def test_contact_sheet_accepts_versioned_data_and_legacy_list(self) -> None:
        item = review_item(1)
        versioned = {"schema_version": CONTACT_SHEET_SCHEMA_VERSION, "items": [item]}

        html = build_contact_sheet_html(versioned, recommended_shots=[1])
        legacy_sanity = visual_selection_sanity([item], recommended_shots=[1])

        self.assertIn("Shot 1", html)
        self.assertTrue(legacy_sanity["ok"])

    def test_contact_sheet_rejects_unsupported_future_version(self) -> None:
        versioned = {"schema_version": "99.0", "items": [review_item(1)]}

        with self.assertRaisesRegex(ValueError, "Unsupported contact sheet schema version"):
            build_contact_sheet_html(versioned, recommended_shots=[1])

    def test_lightroom_plan_accepts_current_handoff_version_and_legacy_review_like_dict(self) -> None:
        handoff = sample_handoff()
        legacy_review_like = {
            "selection": {"recommended_set": [4]},
            "items": [
                {
                    "trainer_shot": 4,
                    "recommended": True,
                    "role": "massing_medium",
                    "filename": "DSC00004.ARW",
                    "edit_intent": {
                        "status": "planned",
                        "develop_settings_planned": {"Texture": 12},
                    },
                }
            ],
        }

        markdown = lightroom_plan_to_markdown(handoff)
        rows = list(csv.DictReader(io.StringIO(lightroom_plan_to_csv(legacy_review_like))))

        self.assertIn("Recommended set: 1", markdown)
        self.assertEqual(rows[0]["trainer_shot"], "4")

    def test_lightroom_plan_accepts_native_current_version(self) -> None:
        plan = {
            "schema_version": LIGHTROOM_PLAN_SCHEMA_VERSION,
            "selection": {"recommended_set": [5]},
            "photos": [
                {
                    "trainer_shot": 5,
                    "recommended": True,
                    "role": "wide_context",
                    "filename": "DSC00005.ARW",
                    "edit_intent": {
                        "status": "planned",
                        "develop_settings_planned": {"Texture": 8},
                    },
                }
            ],
        }

        markdown = lightroom_plan_to_markdown(plan)

        self.assertIn("Recommended set: 5", markdown)

    def test_lightroom_plan_rejects_unsupported_future_version(self) -> None:
        handoff = sample_handoff()
        handoff["schema_version"] = "99.0"

        with self.assertRaisesRegex(ValueError, "Unsupported Lightroom plan source schema version"):
            lightroom_plan_to_markdown(handoff)


def sample_handoff() -> dict:
    handoff = build_adobe_mcp_handoff(
        {"items": [review_item(1)]},
        slug="field-test",
        recommended_shots=[1],
    )
    return copy.deepcopy(handoff)


def review_item(shot: int) -> dict:
    return {
        "plan": {"shot": shot},
        "role": "wide",
        "status": "candidate",
        "source": f"/shoot/DSC{shot:05d}.ARW",
        "metadata": {
            "filename": f"DSC{shot:05d}.ARW",
            "focal_length": 28,
            "orientation": "horizontal",
            "camera": "Sony",
            "lens": "28-75mm",
        },
        "image_analysis": {
            "available": True,
            "tone": "balanced",
            "contrast": 150,
            "highlight_clip_pct": 0,
            "shadow_clip_pct": 0,
        },
    }


def old_v0_1_report_shape() -> dict:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mission": {
            "title": "28-75 Field Map",
            "objective": "Practice deliberate focal length selection.",
        },
        "analysis": {
            "photos": [
                {
                    "relative_path": "frame_28mm.png",
                    "width": 1200,
                    "height": 800,
                    "orientation": "landscape",
                    "megapixels": 0.96,
                    "focal_length_mm": 28,
                    "warnings": [],
                }
            ],
            "unsupported_files": [],
        },
        "scorecard": {
            "total_score": 80,
            "component_scores": {"volume": 100},
            "observations": ["Good structural pass."],
            "duplicate_groups": [],
        },
        "recommendations": ["Repeat the loop."],
        "next_mission": {
            "title": "Next Mission",
            "objective": "Keep practicing.",
        },
    }


def issue_codes(issues: list[dict]) -> set[str]:
    return {issue["code"] for issue in issues}


if __name__ == "__main__":
    unittest.main()
