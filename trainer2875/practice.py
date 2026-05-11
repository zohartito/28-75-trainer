from __future__ import annotations

from copy import deepcopy
from typing import Any

from .mission import mission_for_focus
from .models import Mission


SESSION_HISTORY_SCHEMA_VERSION = "0.1"
SESSION_RECORD_SCHEMA_VERSION = "0.1"
FIRST_WEEK_FOCUSES = ("28mm", "50mm", "75mm")


def first_week_path() -> tuple[Mission, ...]:
    return tuple(mission_for_focus(focus) for focus in FIRST_WEEK_FOCUSES)


def empty_session_history() -> dict[str, Any]:
    return {"schema_version": SESSION_HISTORY_SCHEMA_VERSION, "sessions": []}


def record_session(
    history: dict[str, Any] | None,
    *,
    mission: Mission,
    report_path: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    next_history = empty_session_history() if history is None else deepcopy(history)
    validate_session_history(next_history)
    next_history["sessions"].append(
        {
            "schema_version": SESSION_RECORD_SCHEMA_VERSION,
            "mission_id": mission.mission_id,
            "mission_title": mission.title,
            "target_focal_lengths": list(mission.target_focal_lengths),
            "report_path": report_path,
            "completed_at": completed_at,
        }
    )
    return next_history


def next_first_week_mission(history: dict[str, Any]) -> Mission:
    validate_session_history(history)
    completed = {
        session.get("mission_id")
        for session in history["sessions"]
        if isinstance(session, dict)
    }
    path = first_week_path()
    for mission in path:
        if mission.mission_id not in completed:
            return mission
    return path[-1]


def validate_session_history(history: Any) -> None:
    if not isinstance(history, dict):
        raise ValueError("Session history must be an object.")
    if history.get("schema_version") != SESSION_HISTORY_SCHEMA_VERSION:
        version = history.get("schema_version")
        raise ValueError(f"Unsupported session history schema version: {version}")
    if "sessions" not in history:
        raise ValueError("Session history is missing required field: sessions")
    if not isinstance(history["sessions"], list):
        raise ValueError("Session history field `sessions` must be a list.")
