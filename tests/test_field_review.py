from __future__ import annotations

import unittest
from collections import Counter

from trainer2875.field_review import (
    ALLOWED_DEVELOP_KEYS,
    annotate_similarity_groups,
    build_adobe_mcp_handoff,
    keeper_recall_benchmark,
    recommended_set,
    similarity_groups,
    stable_photo_id,
)


class FieldReviewTests(unittest.TestCase):
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

    def test_similarity_groups_are_separate_from_exact_sha_duplicates(self) -> None:
        reviewed = [
            candidate(1, "wide", sha256="same-sha"),
            candidate(2, "wide", sha256="same-sha"),
        ]

        annotated = annotate_similarity_groups(reviewed)

        self.assertEqual(similarity_groups(reviewed), [])
        self.assertIsNone(annotated[0].get("similarity_group_id"))
        self.assertIsNone(annotated[1].get("similarity_group_id"))

    def test_similarity_groups_identify_adjacent_near_duplicates(self) -> None:
        reviewed = [
            candidate(1, "wide", sha256="sha-a"),
            candidate(2, "wide", sha256="sha-b"),
            candidate(8, "wide", sha256="sha-c"),
        ]

        annotated = annotate_similarity_groups(reviewed)
        near_duplicate_group = annotated[0]["similarity_group_id"]

        self.assertEqual(near_duplicate_group, annotated[1]["similarity_group_id"])
        self.assertIsNone(annotated[2].get("similarity_group_id"))
        self.assertEqual(
            similarity_groups(reviewed),
            [
                {
                    "similarity_group_id": near_duplicate_group,
                    "shots": [1, 2],
                    "role": "wide",
                }
            ],
        )

    def test_low_texture_frames_do_not_group_from_metadata_alone(self) -> None:
        reviewed = [
            candidate(1, "facade", sha256="sha-a", tone="flat", contrast=12),
            candidate(2, "facade", sha256="sha-b", tone="flat", contrast=12),
        ]

        annotated = annotate_similarity_groups(reviewed)

        self.assertIsNone(annotated[0].get("similarity_group_id"))
        self.assertIsNone(annotated[1].get("similarity_group_id"))
        self.assertEqual(similarity_groups(reviewed), [])

    def test_recommended_set_prefers_distinct_similarity_groups(self) -> None:
        reviewed = [
            candidate(1, "wide", sha256="sha-a"),
            candidate(2, "wide", sha256="sha-b"),
            candidate(3, "wide", sha256="sha-c"),
            candidate(20, "wide", sha256="sha-d"),
            candidate(40, "wide", sha256="sha-e"),
        ]

        selected = recommended_set(reviewed, role_targets={"wide": 3})

        self.assertEqual(len(selected), 3)
        self.assertLessEqual(len({1, 2, 3}.intersection(selected)), 1)
        self.assertTrue({20, 40}.issubset(selected))

    def test_recommended_set_uses_same_similarity_group_when_alternatives_are_insufficient(self) -> None:
        reviewed = [
            candidate(1, "wide", sha256="sha-a"),
            candidate(2, "wide", sha256="sha-b"),
            candidate(3, "wide", sha256="sha-c"),
            candidate(20, "wide", sha256="sha-d"),
        ]

        selected = recommended_set(reviewed, role_targets={"wide": 3})

        self.assertEqual(len(selected), 3)
        self.assertEqual(len({1, 2, 3}.intersection(selected)), 2)
        self.assertIn(20, selected)

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

    def test_adobe_mcp_handoff_includes_decision_buckets_with_source_labeled_reasons(self) -> None:
        items = [
            candidate(1, "wide", status="candidate"),
            candidate(2, "wide", status="candidate"),
            candidate(3, "tight", status="warn"),
        ]
        items[2]["warnings"] = ["soft_focus"]

        handoff = build_adobe_mcp_handoff({"items": items}, slug="field-test", recommended_shots=[1])

        self.assertEqual(handoff["decision_buckets"]["counts"]["select"], 1)
        self.assertEqual(handoff["decision_buckets"]["counts"]["maybe"], 1)
        self.assertEqual(handoff["decision_buckets"]["counts"]["practice-evidence"], 1)
        self.assertEqual(handoff["decision_buckets"]["counts"]["reject"], 0)
        by_shot = {photo["trainer_shot"]: photo for photo in handoff["photos"]}
        self.assertEqual(by_shot[1]["decision_bucket"], "select")
        self.assertEqual(by_shot[2]["decision_bucket"], "maybe")
        self.assertEqual(by_shot[3]["decision_bucket"], "practice-evidence")
        self.assertIn("deterministic", reason_sources(by_shot[1]))
        self.assertIn("metadata", reason_sources(by_shot[1]))
        self.assertIn("deterministic_evidence", handoff["decision_buckets"]["reason_source_groups"])
        self.assertIn("human_or_coach_preference", handoff["decision_buckets"]["reason_source_groups"])

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

    def test_adobe_mcp_handoff_exposes_similarity_group_ids(self) -> None:
        items = [
            candidate(1, "wide", sha256="sha-a"),
            candidate(2, "wide", sha256="sha-b"),
            candidate(20, "wide", sha256="sha-c"),
        ]

        handoff = build_adobe_mcp_handoff({"items": items}, slug="field-test", recommended_shots=[1, 20])
        photos_by_shot = {photo["trainer_shot"]: photo for photo in handoff["photos"]}
        group_id = photos_by_shot[1]["similarity_group_id"]

        self.assertIsNotNone(group_id)
        self.assertEqual(group_id, photos_by_shot[2]["similarity_group_id"])
        self.assertIsNone(photos_by_shot[20]["similarity_group_id"])
        self.assertEqual(
            handoff["selection"]["similarity_groups"],
            [{"similarity_group_id": group_id, "shots": [1, 2], "role": "wide"}],
        )

    def test_keeper_recall_reports_false_reject_risk_for_missed_must_keeps(self) -> None:
        benchmark = keeper_recall_benchmark(
            must_keep_photo_ids=["photo-1", "photo-3"],
            recommended_photo_ids=["photo-1", "photo-2"],
            all_photo_ids=["photo-1", "photo-2", "photo-3"],
        )

        self.assertEqual(benchmark["schema_version"], "0.1")
        self.assertEqual(benchmark["must_keep_count"], 2)
        self.assertEqual(benchmark["false_reject_count"], 1)
        self.assertEqual(benchmark["false_rejected_photo_ids"], ["photo-3"])
        self.assertEqual(benchmark["false_reject_risk"], "high")
        self.assertEqual(benchmark["override_count"], 1)
        self.assertEqual(benchmark["override_rate"], 0.5)

    def test_adobe_handoff_includes_keeper_recall_manifest_result(self) -> None:
        missed_keeper = stable_photo_id("field-test", "/shoot/DSC00002.ARW", 2)
        handoff = build_adobe_mcp_handoff(
            {"items": [candidate(1, "wide"), candidate(2, "massing")]},
            slug="field-test",
            recommended_shots=[1],
            must_keep_photo_ids=[missed_keeper],
        )

        keeper_recall = handoff["selection"]["keeper_recall"]
        self.assertEqual(keeper_recall["must_keep_count"], 1)
        self.assertEqual(keeper_recall["false_rejected_photo_ids"], [missed_keeper])
        self.assertEqual(keeper_recall["override_rate"], 1.0)


def candidate(
    shot: int,
    role: str,
    *,
    status: str = "candidate",
    sha256: str | None = None,
    tone: str = "balanced",
    contrast: int = 150,
) -> dict:
    return {
        "plan": {"shot": shot},
        "role": role,
        "status": status,
        "source": f"/shoot/DSC{shot:05d}.ARW",
        "sha256": sha256,
        "metadata": {
            "filename": f"{shot:02d}_DSC{shot:05d}.arw",
            "focal_length": {"wide": 28, "massing": 35, "facade": 50, "tight": 75}[role],
            "orientation": "horizontal",
            "camera": "Sony",
            "lens": "28-75mm",
        },
        "image_analysis": {
            "available": True,
            "tone": tone,
            "contrast": contrast,
            "highlight_clip_pct": 0,
            "shadow_clip_pct": 0,
        },
        "notes": [f"{role} candidate"],
    }


def reason_sources(photo: dict) -> set[str]:
    return {reason["source"] for reason in photo["decision_reasons"]}


if __name__ == "__main__":
    unittest.main()
