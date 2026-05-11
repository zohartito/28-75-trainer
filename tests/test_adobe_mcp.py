from __future__ import annotations

import copy
import unittest

from trainer2875.field_review import build_adobe_mcp_handoff

try:
    from trainer2875.adobe_mcp import dry_run_adobe_mcp_handoff
except ModuleNotFoundError:
    dry_run_adobe_mcp_handoff = None


class AdobeMcpDryRunTests(unittest.TestCase):
    def test_planned_handoff_with_unresolved_catalog_entries_is_ok(self) -> None:
        handoff = sample_handoff()
        handoff["photos"][0]["catalog_path"] = "/catalog/model-001.arw"
        handoff["photos"][0]["uuid"] = "resolved-uuid-001"

        result = self.dry_run(handoff)

        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["recommended_count"], 2)
        self.assertEqual(result["unresolved_catalog_count"], 2)
        self.assertIn("catalog_unresolved", issue_codes(result["warnings"]))

    def test_dry_run_does_not_mutate_the_handoff(self) -> None:
        handoff = sample_handoff()
        original = copy.deepcopy(handoff)

        self.dry_run(handoff)

        self.assertEqual(handoff, original)

    def test_missing_required_top_level_field_is_an_error(self) -> None:
        handoff = sample_handoff()
        del handoff["execution_boundary"]

        result = self.dry_run(handoff)

        self.assertFalse(result["ok"])
        self.assertIn("missing_top_level_field", issue_codes(result["errors"]))

    def test_non_planned_status_is_an_error(self) -> None:
        handoff = sample_handoff()
        handoff["status"] = "executed"

        result = self.dry_run(handoff)

        self.assertFalse(result["ok"])
        self.assertIn("invalid_status", issue_codes(result["errors"]))

    def test_recommended_photo_without_edit_intent_is_an_error(self) -> None:
        handoff = sample_handoff()
        del handoff["photos"][0]["edit_intent"]

        result = self.dry_run(handoff)

        self.assertFalse(result["ok"])
        self.assertIn("missing_edit_intent", issue_codes(result["errors"]))

    def test_unknown_develop_setting_is_an_error(self) -> None:
        handoff = sample_handoff()
        settings = handoff["photos"][0]["edit_intent"]["develop_settings_planned"]
        settings["MadeUpLightroomKey"] = 10

        result = self.dry_run(handoff)

        self.assertFalse(result["ok"])
        self.assertIn("unknown_develop_setting", issue_codes(result["errors"]))

    def test_preview_only_action_in_develop_settings_is_an_error(self) -> None:
        handoff = sample_handoff()
        settings = handoff["photos"][0]["edit_intent"]["develop_settings_planned"]
        settings["AI masks"] = True

        result = self.dry_run(handoff)

        self.assertFalse(result["ok"])
        self.assertIn("preview_only_action_in_develop_settings", issue_codes(result["errors"]))

    def dry_run(self, handoff: dict) -> dict:
        self.assertIsNotNone(dry_run_adobe_mcp_handoff, "dry_run_adobe_mcp_handoff is missing")
        return dry_run_adobe_mcp_handoff(handoff)


def sample_handoff() -> dict:
    return build_adobe_mcp_handoff(
        {"items": [candidate(1, "wide"), candidate(2, "massing"), candidate(3, "tight")]},
        slug="field-test",
        recommended_shots=[1, 3],
    )


def candidate(shot: int, role: str) -> dict:
    return {
        "plan": {"shot": shot},
        "role": role,
        "status": "candidate",
        "source": f"/shoot/DSC{shot:05d}.ARW",
        "metadata": {
            "filename": f"{shot:02d}_DSC{shot:05d}.arw",
            "focal_length": {"wide": 28, "massing": 35, "facade": 50, "tight": 75}[role],
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
        "notes": [f"{role} candidate"],
    }


def issue_codes(issues: list[dict]) -> set[str]:
    return {issue["code"] for issue in issues}


if __name__ == "__main__":
    unittest.main()
