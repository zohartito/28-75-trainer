from __future__ import annotations

import json

from .models import Mission


DEFAULT_MISSION = Mission(
    mission_id="28-75-field-map-v0.1",
    title="28-75 Field Map",
    objective=(
        "Photograph one walkable subject or block across the full zoom range, "
        "then compare how each focal length changes distance, layering, and compression."
    ),
    minimum_shots=12,
    target_focal_lengths=(28, 35, 50, 75),
    constraints=(
        "Shoot at least three frames near each target focal length: 28mm, 35mm, 50mm, and 75mm.",
        "Keep the subject family consistent so differences come from focal length and position.",
        "Include at least one portrait and one landscape frame.",
        "Do not rename, overwrite, or edit originals for the review step.",
    ),
    scoring_weights={
        "volume": 0.2,
        "focal_coverage": 0.35,
        "orientation_variety": 0.15,
        "selection_discipline": 0.15,
        "metadata_completeness": 0.15,
    },
)


def mission_for_focus(focus: str | None = None) -> Mission:
    if not focus:
        return DEFAULT_MISSION
    normalized = focus.strip().lower()
    if normalized in {"wide", "28", "28mm"}:
        return Mission(
            mission_id="28-wide-context-v0.1",
            title="28mm Context Builder",
            objective="Use the wide end to show subject plus context without letting the frame get loose.",
            minimum_shots=10,
            target_focal_lengths=(28,),
            constraints=(
                "Shoot at least ten frames filename-tagged near 28mm.",
                "Change camera position before changing subject.",
                "Make foreground, subject, and background each earn their place.",
                "Do not edit originals for the review step.",
            ),
            scoring_weights={
                "volume": 0.25,
                "focal_coverage": 0.25,
                "orientation_variety": 0.2,
                "selection_discipline": 0.15,
                "metadata_completeness": 0.15,
            },
        )
    if normalized in {"tele", "75", "75mm", "compression"}:
        return Mission(
            mission_id="75-compression-v0.1",
            title="75mm Compression Study",
            objective="Use the long end to simplify backgrounds and make compression and distance choices visible.",
            minimum_shots=10,
            target_focal_lengths=(75,),
            constraints=(
                "Shoot at least ten frames filename-tagged near 75mm.",
                "Make three background-distance changes with the same subject.",
                "Include one tight detail, one half-body/medium view, and one environmental frame.",
                "Do not edit originals for the review step.",
            ),
            scoring_weights={
                "volume": 0.25,
                "focal_coverage": 0.25,
                "orientation_variety": 0.2,
                "selection_discipline": 0.15,
                "metadata_completeness": 0.15,
            },
        )
    if normalized in {"normal", "50", "50mm", "facade"}:
        return Mission(
            mission_id="50-normal-seeing-facade-v0.1",
            title="50mm Normal Seeing / Facade Study",
            objective="Use 50mm to make a facade or primary subject read naturally without wide distortion or long-end compression.",
            minimum_shots=10,
            target_focal_lengths=(50,),
            constraints=(
                "Shoot at least ten frames filename-tagged near 50mm.",
                "Keep verticals and edges intentional; step left, right, closer, and farther before changing subject.",
                "Make one clean facade/context frame, one middle-distance frame, and one tighter read of the same subject.",
                "Do not edit originals for the review step.",
            ),
            scoring_weights={
                "volume": 0.25,
                "focal_coverage": 0.25,
                "orientation_variety": 0.2,
                "selection_discipline": 0.15,
                "metadata_completeness": 0.15,
            },
        )
    return DEFAULT_MISSION


def mission_to_markdown(mission: Mission) -> str:
    constraints = "\n".join(f"- {item}" for item in mission.constraints)
    targets = ", ".join(f"{value}mm" for value in mission.target_focal_lengths)
    weights = "\n".join(
        f"- {name.replace('_', ' ').title()}: {weight:.0%}"
        for name, weight in mission.scoring_weights.items()
    )
    return (
        f"# {mission.title}\n\n"
        f"Mission ID: `{mission.mission_id}`\n\n"
        f"Objective: {mission.objective}\n\n"
        f"Minimum shots: {mission.minimum_shots}\n\n"
        f"Target focal lengths: {targets}\n\n"
        "## Constraints\n\n"
        f"{constraints}\n\n"
        "## Scoring Weights\n\n"
        f"{weights}\n"
    )


def mission_to_json(mission: Mission) -> str:
    return json.dumps(mission.to_dict(), indent=2, sort_keys=True)
