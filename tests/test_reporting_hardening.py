from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from trainer2875.models import REPORT_SCHEMA_VERSION
from trainer2875.reporting import validate_report_data, write_text_output


class ReportingHardeningTests(unittest.TestCase):
    def test_write_text_output_preserves_existing_file_when_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review.html"
            output.write_text("original report", encoding="utf-8")

            with self.assertRaises(UnicodeEncodeError):
                write_text_output(output, "replacement with bad surrogate \udcff")

            self.assertEqual(output.read_text(encoding="utf-8"), "original report")
            self.assertEqual([path.name for path in output.parent.iterdir()], ["review.html"])

    def test_validate_report_data_rejects_missing_nested_schema_fields(self) -> None:
        cases: tuple[tuple[str, tuple[object, ...], str], ...] = (
            ("mission", ("mission", "mission_id"), "mission_id"),
            ("analysis", ("analysis", "root_name"), "root_name"),
            ("analysis photo", ("analysis", "photos", 0, "relative_path"), "relative_path"),
            ("analysis photo", ("analysis", "photos", 0, "warnings"), "warnings"),
            ("scorecard", ("scorecard", "missing_focal_lengths"), "missing_focal_lengths"),
            ("scorecard component_scores", ("scorecard", "component_scores", "volume"), "volume"),
            ("next_mission", ("next_mission", "minimum_shots"), "minimum_shots"),
        )

        for container, path, missing_field in cases:
            with self.subTest(container=container, missing_field=missing_field):
                data = valid_report_data()
                remove_nested(data, path)

                with self.assertRaisesRegex(ValueError, rf"{container}.*{missing_field}"):
                    validate_report_data(data)


def valid_report_data() -> dict[str, object]:
    mission = {
        "mission_id": "field-map-v0.1",
        "title": "28-75 Field Map",
        "objective": "Practice deliberate focal length selection.",
        "minimum_shots": 12,
        "target_focal_lengths": [28, 35, 50, 75],
        "constraints": ["Keep originals untouched."],
        "scoring_weights": {
            "volume": 0.2,
            "focal_coverage": 0.25,
            "orientation_variety": 0.2,
            "selection_discipline": 0.15,
            "metadata_completeness": 0.2,
        },
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mission": deepcopy(mission),
        "analysis": {
            "root_name": "shoot",
            "photos": [
                {
                    "relative_path": "frame_28mm.png",
                    "extension": ".png",
                    "bytes_size": 128,
                    "sha256": "a" * 64,
                    "width": 1200,
                    "height": 800,
                    "orientation": "landscape",
                    "megapixels": 0.96,
                    "focal_length_mm": 28,
                    "aperture": None,
                    "iso": None,
                    "warnings": [],
                }
            ],
            "unsupported_files": [],
        },
        "scorecard": {
            "total_score": 80,
            "component_scores": {
                "volume": 100,
                "focal_coverage": 75,
                "orientation_variety": 100,
                "selection_discipline": 100,
                "metadata_completeness": 75,
            },
            "observations": ["Good structural pass."],
            "duplicate_groups": [],
            "missing_focal_lengths": [35],
        },
        "recommendations": ["Repeat the loop."],
        "next_mission": deepcopy(mission),
    }


def remove_nested(data: dict[str, object], path: tuple[object, ...]) -> None:
    current: object = data
    for key in path[:-1]:
        if isinstance(current, dict):
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int):
            current = current[key]
        else:
            raise AssertionError(f"Unsupported test path segment: {key!r}")
    last = path[-1]
    if isinstance(current, dict):
        del current[last]
        return
    raise AssertionError(f"Unsupported test path leaf: {last!r}")


if __name__ == "__main__":
    unittest.main()
