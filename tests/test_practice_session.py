from __future__ import annotations

import unittest

from trainer2875.mission import mission_for_focus
from trainer2875.practice import (
    SESSION_HISTORY_SCHEMA_VERSION,
    empty_session_history,
    first_week_path,
    next_first_week_mission,
    record_session,
)


class PracticeSessionTests(unittest.TestCase):
    def test_first_week_path_is_context_normal_detail(self) -> None:
        path = first_week_path()

        self.assertEqual(
            [mission.mission_id for mission in path],
            [
                "28-wide-context-v0.1",
                "50-normal-seeing-facade-v0.1",
                "75-compression-v0.1",
            ],
        )
        self.assertEqual([mission.target_focal_lengths for mission in path], [(28,), (50,), (75,)])
        self.assertIn("context", path[0].objective.lower())
        self.assertIn("facade", path[1].objective.lower())
        self.assertIn("compression", path[2].objective.lower())

    def test_session_history_has_schema_version_and_advances_first_week_mission(self) -> None:
        history = empty_session_history()

        self.assertEqual(history["schema_version"], SESSION_HISTORY_SCHEMA_VERSION)
        self.assertEqual(history["sessions"], [])
        self.assertEqual(next_first_week_mission(history).mission_id, "28-wide-context-v0.1")

        first = mission_for_focus("28mm")
        updated = record_session(
            history,
            mission=first,
            report_path="reports/week-1-day-1.json",
            completed_at="2026-05-11T12:00:00Z",
        )

        self.assertEqual(history["sessions"], [])
        self.assertEqual(updated["sessions"][0]["mission_id"], "28-wide-context-v0.1")
        self.assertEqual(updated["sessions"][0]["report_path"], "reports/week-1-day-1.json")
        self.assertEqual(updated["sessions"][0]["completed_at"], "2026-05-11T12:00:00Z")
        self.assertEqual(next_first_week_mission(updated).mission_id, "50-normal-seeing-facade-v0.1")

    def test_session_history_rejects_unknown_schema_version(self) -> None:
        history = {"schema_version": "99.0", "sessions": []}

        with self.assertRaises(ValueError):
            next_first_week_mission(history)


if __name__ == "__main__":
    unittest.main()
