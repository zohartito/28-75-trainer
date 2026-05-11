from __future__ import annotations

import copy
import unittest

from trainer2875.field_review import build_adobe_mcp_handoff

try:
    from trainer2875.adobe_mcp import dry_run_adobe_mcp_handoff
except ModuleNotFoundError:
    dry_run_adobe_mcp_handoff = None

try:
    from trainer2875.adobe_mcp import (
        validate_adobe_mcp_execution_ledger,
        validate_adobe_mcp_status_transition,
    )
except ImportError:
    validate_adobe_mcp_execution_ledger = None
    validate_adobe_mcp_status_transition = None


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


class AdobeMcpExecutionLedgerTests(unittest.TestCase):
    def test_valid_status_progression_keeps_validation_and_execution_separate(self) -> None:
        handoff = sample_handoff()
        dry_run_result = dry_run_adobe_mcp_handoff(handoff)

        validated = self.validate_transition(
            "planned",
            "validated",
            dry_run_result=dry_run_result,
        )
        applied = self.validate_transition(
            "validated",
            "applied",
            ledger=sample_execution_ledger(final_status="applied"),
        )
        complete = self.validate_transition(
            "applied",
            "complete",
            ledger=sample_execution_ledger(final_status="complete"),
        )

        self.assertTrue(validated["ok"])
        self.assertTrue(applied["ok"])
        self.assertTrue(complete["ok"])

    def test_validated_status_requires_successful_dry_run_result(self) -> None:
        result = self.validate_transition(
            "planned",
            "validated",
            dry_run_result={"ok": False, "errors": [{"code": "invalid_status"}]},
        )

        self.assertFalse(result["ok"])
        self.assertIn("dry_run_not_validated", issue_codes(result["errors"]))

    def test_invalid_transition_cannot_skip_applied_status(self) -> None:
        result = self.validate_transition(
            "validated",
            "complete",
            ledger=sample_execution_ledger(final_status="complete"),
        )

        self.assertFalse(result["ok"])
        self.assertIn("invalid_status_transition", issue_codes(result["errors"]))

    def test_applied_status_requires_catalog_copy_snapshot_and_settings_records(self) -> None:
        ledger = sample_execution_ledger(final_status="applied")
        ledger["photos"][0]["uuid"] = None
        ledger["photos"][0]["virtual_copy_id"] = None
        ledger["photos"][0]["snapshot_id"] = None
        ledger["photos"][0]["settings_applied"] = {}

        result = self.validate_ledger(ledger, required_status="applied")

        self.assertFalse(result["ok"])
        self.assertIn("missing_catalog_resolution", issue_codes(result["errors"]))
        self.assertIn("missing_virtual_copy", issue_codes(result["errors"]))
        self.assertIn("missing_snapshot", issue_codes(result["errors"]))
        self.assertIn("missing_settings_applied", issue_codes(result["errors"]))

    def test_complete_status_requires_proof_exports(self) -> None:
        ledger = sample_execution_ledger(final_status="complete", proof_exports=False)

        result = self.validate_transition("applied", "complete", ledger=ledger)

        self.assertFalse(result["ok"])
        self.assertIn("missing_proof_export", issue_codes(result["errors"]))

    def test_complete_status_requires_ledger_confirmation(self) -> None:
        ledger = sample_execution_ledger(final_status="complete", ledger_confirmed=False)

        result = self.validate_transition("applied", "complete", ledger=ledger)

        self.assertFalse(result["ok"])
        self.assertIn("missing_ledger_confirmation", issue_codes(result["errors"]))

    def test_ledger_rejects_unsupported_schema_version(self) -> None:
        ledger = sample_execution_ledger(final_status="applied")
        ledger["schema_version"] = "9.9"

        result = self.validate_ledger(ledger, required_status="applied")

        self.assertFalse(result["ok"])
        self.assertIn("unsupported_schema_version", issue_codes(result["errors"]))

    def validate_transition(self, current_status: str, next_status: str, **kwargs: dict) -> dict:
        self.assertIsNotNone(
            validate_adobe_mcp_status_transition,
            "validate_adobe_mcp_status_transition is missing",
        )
        return validate_adobe_mcp_status_transition(current_status, next_status, **kwargs)

    def validate_ledger(self, ledger: dict, **kwargs: dict) -> dict:
        self.assertIsNotNone(
            validate_adobe_mcp_execution_ledger,
            "validate_adobe_mcp_execution_ledger is missing",
        )
        return validate_adobe_mcp_execution_ledger(ledger, **kwargs)


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


def sample_execution_ledger(
    *,
    final_status: str,
    proof_exports: bool = True,
    ledger_confirmed: bool = True,
) -> dict:
    handoff = sample_handoff()
    photos = []
    for photo in handoff["photos"]:
        if not photo["recommended"]:
            continue
        shot = photo["trainer_shot"]
        photos.append(
            {
                "photo_id": photo["photo_id"],
                "status": final_status,
                "catalog_path": f"/catalog/{photo['filename']}",
                "uuid": f"uuid-{shot}",
                "catalog_resolution_status": "resolved",
                "virtual_copy_id": f"vc-{shot}",
                "snapshot_id": f"snapshot-{shot}",
                "settings_applied": photo["edit_intent"]["develop_settings_planned"],
                "proof_export_paths": [f"/proofs/{photo['photo_id']}.jpg"] if proof_exports else [],
                "failures": [],
            }
        )
    return {
        "handoff_type": "adobe_mcp_run_ledger",
        "schema_version": "0.1",
        "status": final_status,
        "final_status": final_status,
        "ledger_confirmed": ledger_confirmed,
        "photos": photos,
        "failures": [],
    }


def issue_codes(issues: list[dict]) -> set[str]:
    return {issue["code"] for issue in issues}


if __name__ == "__main__":
    unittest.main()
