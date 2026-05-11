from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .field_review import build_adobe_mcp_handoff, recommended_set
from .reporting import validate_review_output_locations, write_text_output

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
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_field_review_data(data)
    return data


def validate_field_review_data(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("Field review JSON must be an object.")
    if "items" not in data:
        raise ValueError("Field review JSON is missing required field: items")
    if not isinstance(data["items"], list):
        raise ValueError("Field review JSON field `items` must be a list.")


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
