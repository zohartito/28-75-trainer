from __future__ import annotations

import unittest

from trainer2875.decision_buckets import BUCKET_NAMES, build_decision_buckets


class DecisionBucketTests(unittest.TestCase):
    def test_builds_visible_buckets_with_source_labeled_reasons(self) -> None:
        items = [
            reviewed_item(1, "wide", status="candidate", focal_length=28),
            reviewed_item(2, "facade", status="candidate", focal_length=50),
            reviewed_item(3, "tight", status="warn", focal_length=75, warnings=["soft_focus"]),
            reviewed_item(4, "unknown", status="rejected", focal_length=None),
        ]

        buckets = build_decision_buckets(
            items,
            selected_shots=[1],
            coach_preferences={2: ["Coach likes the facade rhythm as an alternate."]},
            overrides=[
                {
                    "trainer_shot": 3,
                    "bucket": "reject",
                    "reason": "User removed the soft detail from this round.",
                }
            ],
        )

        self.assertEqual(list(buckets["buckets"]), list(BUCKET_NAMES))
        self.assertEqual(bucket_shots(buckets, "select"), [1])
        self.assertEqual(bucket_shots(buckets, "maybe"), [2])
        self.assertEqual(bucket_shots(buckets, "reject"), [3, 4])
        self.assertEqual(bucket_shots(buckets, "practice-evidence"), [])

        every_item = [item for bucket in buckets["buckets"].values() for item in bucket]
        self.assertTrue(every_item)
        for item in every_item:
            self.assertIn(item["bucket"], BUCKET_NAMES)
            self.assertTrue(item["reasons"])
            self.assertTrue(all(reason.get("source") for reason in item["reasons"]))

        selected = buckets["buckets"]["select"][0]
        self.assertEqual(selected["deterministic_bucket"], "select")
        self.assertIn("deterministic", reason_sources(selected))
        self.assertIn("metadata", reason_sources(selected))

        maybe = buckets["buckets"]["maybe"][0]
        self.assertEqual(maybe["deterministic_bucket"], "maybe")
        self.assertIn("coach_preference", reason_sources(maybe))

        override = buckets["buckets"]["reject"][0]
        self.assertEqual(override["trainer_shot"], 3)
        self.assertEqual(override["deterministic_bucket"], "practice-evidence")
        self.assertIn("user_override", reason_sources(override))

        self.assertNotIn("bucket", items[2])
        self.assertNotIn("decision_reasons", items[2])

    def test_uses_existing_recommended_flags_when_selected_shots_are_omitted(self) -> None:
        items = [
            reviewed_item(1, "wide", status="candidate", focal_length=28),
            reviewed_item(2, "wide", status="candidate", focal_length=28),
        ]
        items[1]["recommended"] = True

        buckets = build_decision_buckets(items)

        self.assertEqual(bucket_shots(buckets, "select"), [2])
        self.assertEqual(bucket_shots(buckets, "maybe"), [1])


def reviewed_item(
    shot: int,
    role: str,
    *,
    status: str,
    focal_length: int | None,
    warnings: list[str] | None = None,
) -> dict:
    return {
        "trainer_shot": shot,
        "role": role,
        "status": status,
        "source": f"/shoot/DSC{shot:05d}.ARW",
        "metadata": {
            "filename": f"DSC{shot:05d}.ARW",
            "focal_length": focal_length,
            "orientation": "horizontal",
        },
        "warnings": warnings or [],
    }


def bucket_shots(buckets: dict, bucket_name: str) -> list[int]:
    return [item["trainer_shot"] for item in buckets["buckets"][bucket_name]]


def reason_sources(item: dict) -> set[str]:
    return {reason["source"] for reason in item["reasons"]}


if __name__ == "__main__":
    unittest.main()
