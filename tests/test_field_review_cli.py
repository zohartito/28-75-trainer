from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class FieldReviewCliTests(unittest.TestCase):
    def test_cli_writes_planned_adobe_mcp_handoff_for_extra_photo_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shoot = work / "shoot"
            shoot.mkdir()
            review_path = work / "field-review.json"
            handoff_path = work / "adobe-mcp-handoff.json"

            originals = {}
            items = []
            for shot, role in [
                (1, "wide"),
                (2, "wide"),
                (3, "wide"),
                (4, "wide"),
                (5, "massing"),
                (6, "massing"),
                (7, "massing"),
                (8, "facade"),
                (9, "facade"),
                (10, "facade"),
                (11, "tight"),
                (12, "tight"),
                (13, "tight"),
            ]:
                source = shoot / f"DSC{shot:05d}.ARW"
                source.write_bytes(f"original-{shot}".encode("utf-8"))
                originals[source] = source.read_bytes()
                items.append(candidate(shot, role, source))
            review_path.write_text(json.dumps({"items": items}), encoding="utf-8")

            result = run_cli(
                "field-review",
                str(review_path),
                "--slug",
                "sunlight-model",
                "--adobe-mcp-out",
                str(handoff_path),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({path: path.read_bytes() for path in originals}, originals)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "planned")
            self.assertEqual(summary["item_count"], 13)
            self.assertEqual(summary["recommended_set"], [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
            self.assertEqual(summary["adobe_mcp_handoff"], str(handoff_path))
            self.assertFalse(summary["lightroom_completion_claim_allowed"])

            handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
            self.assertEqual(handoff["status"], "planned")
            self.assertEqual(handoff["shoot"]["recommended_count"], 12)
            self.assertEqual(handoff["selection"]["recommended_set"], summary["recommended_set"])
            self.assertFalse(handoff["execution_boundary"]["lightroom_completion_claim_allowed"])
            self.assertTrue(all(photo["status"] == "planned" for photo in handoff["photos"]))
            self.assertTrue(all(photo["catalog_path"] is None for photo in handoff["photos"]))
            self.assertTrue(any(not photo["recommended"] for photo in handoff["photos"]))
            self.assertNotIn("completed", result.stdout.lower())
            self.assertNotIn("completed", handoff_path.read_text(encoding="utf-8").lower())

    def test_cli_rejects_adobe_mcp_output_inside_source_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shoot = work / "shoot"
            shoot.mkdir()
            review_path = work / "field-review.json"
            blocked_handoff_path = shoot / "adobe-mcp-handoff.json"
            source = shoot / "DSC00001.ARW"
            source.write_bytes(b"original")
            review_path.write_text(json.dumps({"items": [candidate(1, "wide", source)]}), encoding="utf-8")

            result = run_cli(
                "field-review",
                str(review_path),
                "--adobe-mcp-out",
                str(blocked_handoff_path),
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(source.read_bytes(), b"original")
            self.assertFalse(blocked_handoff_path.exists())
            self.assertIn("inside the reviewed folder", result.stderr)

    def test_cli_rejects_review_json_without_items_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            review_path = Path(tmp) / "field-review.json"
            review_path.write_text(json.dumps({"items": {"not": "a list"}}), encoding="utf-8")

            result = run_cli("field-review", str(review_path))

            self.assertEqual(result.returncode, 2)
            self.assertIn("items", result.stderr)

    def test_cli_rejects_duplicate_identity_and_non_finite_nested_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            source = work / "DSC00001.ARW"
            source.write_bytes(b"original")
            duplicate = candidate(1, "wide", source)
            duplicate["source"] = str(work / "other.ARW")
            review_path = work / "duplicates.json"
            review_path.write_text(json.dumps({"items": [candidate(1, "wide", source), duplicate]}), encoding="utf-8")
            result = run_cli("field-review", str(review_path))
            self.assertEqual(result.returncode, 2)
            self.assertIn("duplicates trainer shot", result.stderr)

            malformed = candidate(2, "wide", source)
            malformed["image_analysis"]["contrast"] = float("inf")
            review_path.write_text(json.dumps({"items": [malformed]}), encoding="utf-8")
            result = run_cli("field-review", str(review_path))
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid", result.stderr)

    def test_cli_rejects_out_of_range_and_huge_json_ranking_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            source = work / "DSC00001.ARW"
            source.write_bytes(b"original")
            review_path = work / "invalid-ranges.json"
            malformed = candidate(1, "wide", source)
            malformed["image_analysis"]["highlight_clip_pct"] = -1
            review_path.write_text(json.dumps({"items": [malformed]}), encoding="utf-8")
            result = run_cli("field-review", str(review_path))
            self.assertEqual(result.returncode, 2)
            self.assertIn("highlight_clip_pct", result.stderr)

            malformed = candidate(1, "wide", source)
            malformed["image_analysis"]["contrast"] = 10**1000
            review_path.write_text(json.dumps({"items": [malformed]}), encoding="utf-8")
            result = run_cli("field-review", str(review_path))
            self.assertEqual(result.returncode, 2)
            self.assertIn("finite", result.stderr)


def candidate(shot: int, role: str, source: Path) -> dict:
    return {
        "plan": {"shot": shot},
        "role": role,
        "status": "candidate",
        "source": str(source),
        "metadata": {
            "filename": source.name,
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
    }


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "trainer2875", *args],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )


if __name__ == "__main__":
    unittest.main()
