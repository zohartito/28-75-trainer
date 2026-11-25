from __future__ import annotations

import unittest
from collections import Counter

from trainer2875.field_review import ALLOWED_DEVELOP_KEYS, build_adobe_mcp_handoff, recommended_set


class FieldReviewTests(unittest.TestCase):
    def test_explicit_empty_handoff_selection_is_preserved(self) -> None:
        review = {"items": [candidate(1, "wide"), candidate(2, "tight")]}
        self.assertTrue(build_adobe_mcp_handoff(review, slug="test")["selection"]["recommended_set"])
        handoff = build_adobe_mcp_handoff(review, slug="test", recommended_shots=[])
        self.assertEqual(handoff["selection"]["recommended_set"], [])
        self.assertEqual(handoff["shoot"]["recommended_count"], 0)
        self.assertTrue(all(not photo["recommended"] for photo in handoff["photos"]))

    def test_recommended_set_spreads_role_picks_across_the_full_shoot(self) -> None:
        reviewed = []
        for role, shots in {
            "wide": [1, 2, 3, 30, 31, 32],
            "massing": [4, 5, 6],
            "facade": [7, 8, 9, 40, 41, 42],
            "tight": [10, 11, 12, 50, 51, 52],
        }.items():
            for shot in shots:
                reviewed.append(candidate(shot, role))

        selected = recommended_set(reviewed)

        self.assertEqual(len(selected), 12)
        self.assertNotEqual(selected, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        self.assertTrue(any(shot >= 30 for shot in selected if shot in {1, 2, 3, 30, 31, 32}))
        self.assertTrue(any(shot >= 40 for shot in selected if shot in {7, 8, 9, 40, 41, 42}))
        self.assertTrue(any(shot >= 50 for shot in selected if shot in {10, 11, 12, 50, 51, 52}))

    def test_adobe_mcp_handoff_is_planned_and_catalog_unresolved(self) -> None:
        items = []
        for role, shots in {
            "wide": [15, 30, 36],
            "massing": [16, 21, 43],
            "facade": [7, 27, 39],
            "tight": [23, 31, 54],
        }.items():
            for shot in shots:
                items.append(candidate(shot, role, status="candidate"))

        handoff = build_adobe_mcp_handoff(
            {"items": items},
            slug="field-test",
            recommended_shots=[7, 15, 16, 21, 23, 27, 30, 31, 36, 39, 43, 54],
            stale_recommended_sets=[[1, 7, 11, 13, 14, 15, 17, 18, 19, 20, 21, 25]],
        )

        recommended = [photo for photo in handoff["photos"] if photo["recommended"]]
        self.assertEqual(handoff["status"], "planned")
        self.assertEqual(len(recommended), 12)
        self.assertEqual(
            Counter(photo["role"] for photo in recommended),
            {
                "wide_context": 3,
                "massing_medium": 3,
                "facade_detail_context": 3,
                "tight_detail_compression": 3,
            },
        )
        self.assertTrue(all(photo["uuid"] is None for photo in handoff["photos"]))
        self.assertTrue(all(photo["catalog_path"] is None for photo in handoff["photos"]))
        self.assertTrue(all(photo["status"] == "planned" for photo in handoff["photos"]))
        self.assertTrue(all(photo["edit_intent"]["status"] == "planned" for photo in recommended))
        for photo in recommended:
            self.assertLessEqual(set(photo["edit_intent"]["develop_settings_planned"]), ALLOWED_DEVELOP_KEYS)

    def test_recommended_unknown_role_stays_planned_without_crashing(self) -> None:
        item = candidate(99, "tight")
        item["role"] = "unknown"
        item["metadata"]["focal_length"] = None

        handoff = build_adobe_mcp_handoff({"items": [item]}, slug="field-test", recommended_shots=[99])

        photo = handoff["photos"][0]
        self.assertTrue(photo["recommended"])
        self.assertEqual(photo["role"], "unknown")
        self.assertEqual(photo["edit_intent"]["status"], "planned")
        self.assertLessEqual(set(photo["edit_intent"]["develop_settings_planned"]), ALLOWED_DEVELOP_KEYS)


def candidate(shot: int, role: str, *, status: str = "candidate") -> dict:
    return {
        "plan": {"shot": shot},
        "role": role,
        "status": status,
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


if __name__ == "__main__":
    unittest.main()
