from __future__ import annotations

from .mission import mission_for_focus
from .models import CoachingReport, FolderAnalysis, Mission
from .scoring import score_analysis


def build_coaching_report(analysis: FolderAnalysis, mission: Mission) -> CoachingReport:
    scorecard = score_analysis(analysis, mission)
    recommendations = recommendations_for(scorecard)
    next_mission = next_mission_for(scorecard)
    return CoachingReport(
        mission=mission,
        analysis=analysis,
        scorecard=scorecard,
        recommendations=tuple(recommendations),
        next_mission=next_mission,
    )


def recommendations_for(scorecard) -> list[str]:
    recommendations: list[str] = []
    components = scorecard.component_scores
    if components["focal_coverage"] < 100:
        missing = ", ".join(f"{value}mm" for value in scorecard.missing_focal_lengths)
        recommendations.append(f"Reshoot with intentional coverage at {missing}; make the zoom choice before raising the camera.")
    if components["orientation_variety"] < 100:
        recommendations.append("Pair each setup with one landscape frame and one portrait frame before moving on.")
    if components["selection_discipline"] < 90:
        recommendations.append(
            "Remove exact byte-identical duplicate files before reading the score; v0.1 does not compare near-duplicates or choose the best frame."
        )
    if components["metadata_completeness"] < 80:
        recommendations.append("Add focal-length filename tags such as `28mm` or preserve EXIF so the next review can be more specific.")
    if components["volume"] < 100:
        recommendations.append("Finish the repetition count before judging the exercise; the loop needs enough attempts to reveal a pattern.")
    if not recommendations:
        recommendations.append("Good structural pass: repeat the subject type in different light and raise the constraint difficulty.")
    return recommendations


def next_mission_for(scorecard) -> Mission:
    components = scorecard.component_scores
    if components["focal_coverage"] < 100 and scorecard.missing_focal_lengths:
        if min(scorecard.missing_focal_lengths) <= 35:
            return mission_for_focus("wide")
        return mission_for_focus("75mm")
    if components["orientation_variety"] < 100:
        return Mission(
            mission_id="orientation-pairing-v0.1",
            title="Orientation Pairing",
            objective="Create one landscape and one portrait version before leaving each setup.",
            minimum_shots=12,
            target_focal_lengths=(28, 50, 75),
            constraints=(
                "For each chosen subject, shoot a landscape and portrait frame.",
                "Change body position between the pair instead of only cropping with zoom.",
                "Keep all originals untouched for review.",
            ),
            scoring_weights={
                "volume": 0.2,
                "focal_coverage": 0.25,
                "orientation_variety": 0.3,
                "selection_discipline": 0.1,
                "metadata_completeness": 0.15,
            },
        )
    if components["selection_discipline"] < 90:
        return Mission(
            mission_id="one-frame-reason-v0.1",
            title="One-Frame Reason",
            objective="Reduce accidental exact duplicates before interpreting selection discipline.",
            minimum_shots=8,
            target_focal_lengths=(35, 50, 75),
            constraints=(
                "Shoot no more than two frames per setup.",
                "Change distance, angle, or timing before making the second frame.",
                "Keep all originals untouched for review.",
            ),
            scoring_weights={
                "volume": 0.2,
                "focal_coverage": 0.2,
                "orientation_variety": 0.15,
                "selection_discipline": 0.3,
                "metadata_completeness": 0.15,
            },
        )
    return mission_for_focus("tele")
