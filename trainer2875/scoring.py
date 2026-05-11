from __future__ import annotations

from collections import Counter, defaultdict

from .models import FolderAnalysis, Mission, ScoreCard


def score_analysis(analysis: FolderAnalysis, mission: Mission) -> ScoreCard:
    photos = analysis.photos
    total = len(photos)
    volume_score = round(min(total / mission.minimum_shots, 1.0) * 100) if mission.minimum_shots else 100

    covered_targets = covered_focal_targets(analysis, mission)
    target_count = max(len(mission.target_focal_lengths), 1)
    focal_coverage_score = round((len(covered_targets) / target_count) * 100)
    missing = tuple(target for target in mission.target_focal_lengths if target not in covered_targets)

    orientations = {photo.orientation for photo in photos if photo.orientation != "unknown"}
    orientation_score = 100 if {"landscape", "portrait"}.issubset(orientations) else 50 if orientations else 0

    duplicate_groups = exact_duplicate_groups(analysis)
    duplicate_photo_count = sum(len(group) for group in duplicate_groups)
    duplicate_penalty = min(duplicate_photo_count / max(total, 1), 1.0)
    selection_score = 0 if total == 0 else round((1.0 - duplicate_penalty) * 100)

    dimension_known = sum(1 for photo in photos if photo.has_readable_dimensions)
    focal_known = sum(1 for photo in photos if photo.focal_length_mm is not None)
    metadata_score = round((((dimension_known + focal_known) / 2) / max(total, 1)) * 100)

    components = {
        "volume": volume_score,
        "focal_coverage": focal_coverage_score,
        "orientation_variety": orientation_score,
        "selection_discipline": selection_score,
        "metadata_completeness": metadata_score,
    }
    total_score = round(
        sum(components[name] * mission.scoring_weights.get(name, 0.0) for name in components)
    )
    observations = build_observations(analysis, components, duplicate_groups, missing)
    return ScoreCard(
        total_score=total_score,
        component_scores=components,
        observations=tuple(observations),
        duplicate_groups=tuple(tuple(group) for group in duplicate_groups),
        missing_focal_lengths=missing,
    )


def covered_focal_targets(analysis: FolderAnalysis, mission: Mission) -> set[int]:
    covered: set[int] = set()
    for photo in analysis.photos:
        if not photo.has_readable_dimensions:
            continue
        if photo.focal_length_mm is None:
            continue
        nearest = min(mission.target_focal_lengths, key=lambda target: abs(target - photo.focal_length_mm))
        tolerance = 4 if nearest < 60 else 6
        if abs(photo.focal_length_mm - nearest) <= tolerance:
            covered.add(nearest)
    return covered


def exact_duplicate_groups(analysis: FolderAnalysis) -> list[list[str]]:
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for photo in analysis.photos:
        groups[photo.sha256].append(photo.relative_path)
    return [sorted(paths) for paths in groups.values() if len(paths) > 1]


def build_observations(
    analysis: FolderAnalysis,
    components: dict[str, int],
    duplicate_groups: list[list[str]],
    missing_focal_lengths: tuple[int, ...],
) -> list[str]:
    observations: list[str] = []
    total = len(analysis.photos)
    if total == 0:
        observations.append(
            f"Reviewed 0 recognized image file(s); skipped {len(analysis.unsupported_files)} unsupported file(s). "
            "There is not enough evidence to score this practice loop."
        )
        return observations
    observations.append(f"Reviewed {total} recognized image file(s); skipped {len(analysis.unsupported_files)} unsupported file(s).")
    focal_counts = Counter(photo.focal_length_mm for photo in analysis.photos if photo.focal_length_mm is not None)
    if focal_counts:
        spread = ", ".join(f"{focal}mm: {count}" for focal, count in sorted(focal_counts.items()))
        observations.append(f"Detected focal-length tags: {spread}.")
    else:
        observations.append("No focal-length tags were detected; add filename tags or future EXIF parsing for stronger coaching.")
    if missing_focal_lengths:
        missing = ", ".join(f"{value}mm" for value in missing_focal_lengths)
        observations.append(f"Missing target focal lengths: {missing}.")
    if duplicate_groups:
        observations.append(
            f"Found {len(duplicate_groups)} exact byte-identical duplicate group(s) by SHA-256; "
            "remove accidental copies before interpreting selection discipline."
        )
    weak_components = [name for name, value in components.items() if value < 70]
    if weak_components:
        labels = ", ".join(name.replace("_", " ") for name in weak_components)
        observations.append(f"Best next improvement areas: {labels}.")
    return observations
