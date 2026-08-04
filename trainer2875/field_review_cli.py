from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from .field_review import MAX_CLIP_PERCENT, MAX_REVIEW_CONTRAST, MAX_REVIEW_FOCAL_LENGTH_MM, build_adobe_mcp_handoff, recommended_set, require_range
from .reporting import validate_review_output_locations, write_text_output
from .safeio import MAX_JSON_BYTES, MAX_REVIEW_FILES, load_json_object

FIELD_REVIEW_SUMMARY_SCHEMA_VERSION = "0.1"


def run_field_review(args: Any) -> int:
    review_path = Path(args.review_json).expanduser()
    review = load_field_review_json(review_path)
    slug = args.slug or review.get("slug") or review_path.stem
    recommended_shots = recommended_set(review["items"])
    adobe_mcp_out = Path(args.adobe_mcp_out).expanduser() if args.adobe_mcp_out else None

    if adobe_mcp_out:
        validate_field_review_output_locations(review, review_path, adobe_mcp_out)
        handoff_review = dict(review)
        handoff_review.setdefault("source_report_json", str(review_path))
        handoff = build_adobe_mcp_handoff(
            handoff_review,
            slug=slug,
            recommended_shots=recommended_shots,
        )
        write_text_output(adobe_mcp_out, json.dumps(handoff, indent=2, sort_keys=True))

    summary = build_field_review_summary(
        review,
        review_path=review_path,
        slug=slug,
        recommended_shots=recommended_shots,
        adobe_mcp_out=adobe_mcp_out,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def load_field_review_json(path: str | Path) -> dict[str, Any]:
    data = load_json_object(path, max_bytes=MAX_JSON_BYTES)
    validate_field_review_data(data)
    return data


def validate_field_review_data(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("Field review JSON must be an object.")
    if "items" not in data:
        raise ValueError("Field review JSON is missing required field: items")
    if not isinstance(data["items"], list):
        raise ValueError("Field review JSON field `items` must be a list.")
    if len(data["items"]) > MAX_REVIEW_FILES:
        raise ValueError(f"Field review JSON exceeds the {MAX_REVIEW_FILES} item limit.")
    seen_shots: set[int] = set()
    seen_sources: set[str] = set()
    for index, item in enumerate(data["items"]):
        validate_field_review_item(item, index)
        shot = field_review_shot(item)
        source = field_review_source(item)
        if shot in seen_shots:
            raise ValueError(f"Field review JSON item {index} duplicates trainer shot {shot}.")
        if source and source in seen_sources:
            raise ValueError(f"Field review JSON item {index} duplicates source identity: {source}")
        seen_shots.add(shot)
        if source:
            seen_sources.add(source)


def validate_field_review_item(item: Any, index: int) -> None:
    if not isinstance(item, dict):
        raise ValueError(f"Field review JSON item {index} must be an object.")
    shot = field_review_shot(item)
    if not 1 <= shot <= 1_000_000:
        raise ValueError(f"Field review JSON item {index} trainer shot is out of range.")
    for key in ("role", "status", "source", "path", "filename"):
        if key in item and item[key] is not None and (not isinstance(item[key], str) or len(item[key]) > 10_000):
            raise ValueError(f"Field review JSON item {index} field `{key}` must be a bounded string.")
    for key in ("warnings", "notes"):
        value = item.get(key, [])
        if not isinstance(value, list) or len(value) > 1_000 or any(not isinstance(note, str) or len(note) > 10_000 for note in value):
            raise ValueError(f"Field review JSON item {index} field `{key}` must be a bounded string list.")
    for key in ("metadata", "image_analysis"):
        value = item.get(key, {})
        if not isinstance(value, dict) or len(value) > 100:
            raise ValueError(f"Field review JSON item {index} field `{key}` must be an object with at most 100 fields.")
        validate_nested_field_values(value, f"Field review JSON item {index} {key}")
    validate_ranking_ranges(item, index)
    if "plan" in item and (not isinstance(item["plan"], dict) or len(item["plan"]) > 20):
        raise ValueError(f"Field review JSON item {index} plan must be an object.")


def validate_nested_field_values(values: dict[str, Any], label: str) -> None:
    for key, value in values.items():
        if not isinstance(key, str) or len(key) > 200:
            raise ValueError(f"{label} has an invalid field name.")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{label} has a non-finite numeric value.")
        if isinstance(value, (dict, list)):
            raise ValueError(f"{label} must not contain nested collections.")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"{label} has an unsupported field value.")
        if isinstance(value, str) and len(value) > 10_000:
            raise ValueError(f"{label} has an overlong string value.")


def validate_ranking_ranges(item: dict[str, Any], index: int) -> None:
    metadata = item.get("metadata") or {}
    stats = item.get("image_analysis") or {}
    for key in ("focal_length", "focal_length_mm"):
        if metadata.get(key) is not None:
            require_range(metadata[key], 1, MAX_REVIEW_FOCAL_LENGTH_MM, f"Field review JSON item {index} {key}")
    if stats.get("contrast") is not None:
        require_range(stats["contrast"], 0, MAX_REVIEW_CONTRAST, f"Field review JSON item {index} contrast")
    for key in ("highlight_clip_pct", "shadow_clip_pct"):
        if stats.get(key) is not None:
            require_range(stats[key], 0, MAX_CLIP_PERCENT, f"Field review JSON item {index} {key}")


def field_review_shot(item: dict[str, Any]) -> int:
    plan = item.get("plan")
    raw = plan.get("shot") if isinstance(plan, dict) and plan.get("shot") is not None else item.get("trainer_shot")
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("Field review item trainer shot must be an integer.")
    return raw


def field_review_source(item: dict[str, Any]) -> str:
    source = item.get("source") or item.get("path") or ""
    return os.path.abspath(os.path.expanduser(source)) if isinstance(source, str) else ""


def build_field_review_summary(
    review: dict[str, Any],
    *,
    review_path: Path,
    slug: str,
    recommended_shots: list[int],
    adobe_mcp_out: Path | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": FIELD_REVIEW_SUMMARY_SCHEMA_VERSION,
        "status": "planned",
        "slug": slug,
        "source_review_json": str(review_path),
        "item_count": len(review["items"]),
        "recommended_count": len(recommended_shots),
        "recommended_set": recommended_shots,
        "adobe_mcp_handoff": str(adobe_mcp_out) if adobe_mcp_out else None,
        "lightroom_completion_claim_allowed": False,
    }


def validate_field_review_output_locations(
    review: dict[str, Any],
    review_path: Path,
    *outputs: str | Path,
) -> None:
    for folder in field_review_source_folders(review, review_path):
        validate_review_output_locations(folder, *outputs)


def field_review_source_folders(review: dict[str, Any], review_path: Path) -> list[Path]:
    folders: list[Path] = []
    for key in ("source_folder", "review_folder", "input_folder", "shoot_folder"):
        value = review.get(key)
        if isinstance(value, str) and value.strip():
            folders.append(resolve_review_relative_path(value, review_path))

    inferred = infer_common_source_folder(review, review_path)
    if inferred:
        folders.append(inferred)

    unique: list[Path] = []
    seen: set[Path] = set()
    for folder in folders:
        resolved = folder.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(folder)
    return unique


def infer_common_source_folder(review: dict[str, Any], review_path: Path) -> Path | None:
    source_parents: list[Path] = []
    for item in review.get("items", []):
        if not isinstance(item, dict):
            continue
        source = item.get("source") or item.get("path")
        if isinstance(source, str) and source.strip():
            source_parents.append(resolve_review_relative_path(source, review_path).parent)
    if not source_parents:
        return None
    try:
        common = os.path.commonpath([str(parent.resolve()) for parent in source_parents])
    except ValueError:
        return None
    return Path(common)


def resolve_review_relative_path(path: str, review_path: Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return review_path.parent / candidate
