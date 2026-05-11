from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPORT_SCHEMA_VERSION = "1.0"
SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".arw",
    ".cr2",
    ".cr3",
    ".dng",
    ".nef",
    ".orf",
    ".raf",
    ".rw2",
    ".pef",
    ".srw",
}


@dataclass(frozen=True)
class Mission:
    mission_id: str
    title: str
    objective: str
    minimum_shots: int
    target_focal_lengths: tuple[int, ...]
    constraints: tuple[str, ...]
    scoring_weights: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "title": self.title,
            "objective": self.objective,
            "minimum_shots": self.minimum_shots,
            "target_focal_lengths": list(self.target_focal_lengths),
            "constraints": list(self.constraints),
            "scoring_weights": self.scoring_weights,
        }


@dataclass(frozen=True)
class PhotoAnalysis:
    path: Path
    relative_path: str
    extension: str
    bytes_size: int
    sha256: str
    width: int | None = None
    height: int | None = None
    dimensions_source: str = "unavailable"
    focal_length_mm: int | None = None
    focal_length_source: str = "unavailable"
    aperture: str | None = None
    iso: int | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_readable_dimensions(self) -> bool:
        return self.width is not None and self.height is not None

    @property
    def orientation(self) -> str:
        if not self.has_readable_dimensions:
            return "unknown"
        if self.width == self.height:
            return "square"
        if self.width > self.height:
            return "landscape"
        return "portrait"

    @property
    def megapixels(self) -> float | None:
        if not self.has_readable_dimensions:
            return None
        return round((self.width * self.height) / 1_000_000, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "extension": self.extension,
            "bytes_size": self.bytes_size,
            "sha256": self.sha256,
            "width": self.width,
            "height": self.height,
            "dimensions_source": self.dimensions_source,
            "orientation": self.orientation,
            "megapixels": self.megapixels,
            "focal_length_mm": self.focal_length_mm,
            "focal_length_source": self.focal_length_source,
            "aperture": self.aperture,
            "iso": self.iso,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class FolderAnalysis:
    root_name: str
    photos: tuple[PhotoAnalysis, ...]
    unsupported_files: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_name": self.root_name,
            "photos": [photo.to_dict() for photo in self.photos],
            "unsupported_files": list(self.unsupported_files),
        }


@dataclass(frozen=True)
class ScoreCard:
    total_score: int
    component_scores: dict[str, int]
    observations: tuple[str, ...]
    duplicate_groups: tuple[tuple[str, ...], ...]
    missing_focal_lengths: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_score": self.total_score,
            "component_scores": self.component_scores,
            "observations": list(self.observations),
            "duplicate_groups": [list(group) for group in self.duplicate_groups],
            "missing_focal_lengths": list(self.missing_focal_lengths),
        }


@dataclass(frozen=True)
class CoachingReport:
    mission: Mission
    analysis: FolderAnalysis
    scorecard: ScoreCard
    recommendations: tuple[str, ...]
    next_mission: Mission

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "mission": self.mission.to_dict(),
            "analysis": self.analysis.to_dict(),
            "scorecard": self.scorecard.to_dict(),
            "recommendations": list(self.recommendations),
            "next_mission": self.next_mission.to_dict(),
        }
