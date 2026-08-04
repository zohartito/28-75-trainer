from __future__ import annotations

import hashlib
import math
from collections import Counter
from pathlib import Path
from typing import Any

ROLE_TARGETS = {"wide": 3, "massing": 3, "facade": 3, "tight": 3}
MAX_REVIEW_FOCAL_LENGTH_MM = 2_000
MAX_REVIEW_CONTRAST = 255
MAX_CLIP_PERCENT = 100

HANDOFF_ROLES = {
    "wide": "wide_context",
    "massing": "massing_medium",
    "facade": "facade_detail_context",
    "tight": "tight_detail_compression",
}

ALLOWED_DEVELOP_KEYS = {
    "EnableLensProfileCorrections",
    "RemoveChromaticAberration",
    "Exposure2012",
    "Contrast2012",
    "Highlights2012",
    "Shadows2012",
    "Whites2012",
    "Blacks2012",
    "Texture",
    "Clarity2012",
    "Dehaze",
    "Vibrance",
    "Saturation",
    "Sharpness",
    "LuminanceSmoothing",
    "Temp",
    "Tint",
    "CropAngle",
    "PerspectiveHorizontal",
    "PerspectiveVertical",
}

ROLE_EDIT_PROFILES = {
    "wide_context": {
        "goal": "Establish the model in its light and context.",
        "style": "Natural architectural documentation with restrained correction.",
        "reason": "Wide/context frames orient the viewer before detail review.",
        "preserve": "Whole model, base, useful shadows, and context.",
        "beginner": "This is the photo that tells viewers what they are looking at.",
        "settings": {"Texture": 8, "Clarity2012": 4, "Sharpness": 40},
    },
    "massing_medium": {
        "goal": "Make the main volume, proportions, and structure readable.",
        "style": "Clear, square, neutral model photography.",
        "reason": "Massing frames explain architectural form better than close details alone.",
        "preserve": "Edges, depth, sun/shadow cues, and overall volume.",
        "beginner": "This should be the clean middle-distance view where the shape makes sense.",
        "settings": {"Texture": 12, "Clarity2012": 6, "Sharpness": 45},
    },
    "facade_detail_context": {
        "goal": "Show a readable face or detail while keeping architectural context.",
        "style": "Natural color, clear texture, and careful geometry.",
        "reason": "Facade/detail-with-context frames connect the design idea to a specific face or system.",
        "preserve": "Adjacent edges and enough model context to understand the detail.",
        "beginner": "This is close enough to see the idea, but not so close that the viewer gets lost.",
        "settings": {"Texture": 18, "Clarity2012": 8, "Sharpness": 55},
    },
    "tight_detail_compression": {
        "goal": "Isolate a strong detail, rhythm, shadow, or compression moment.",
        "style": "Crisp detail read with natural color and controlled highlights.",
        "reason": "Tight frames teach the habit of finding memorable architectural moments.",
        "preserve": "Important edge, shadow rhythm, material texture, and focus-critical detail.",
        "beginner": "Check this at 100 percent; if the detail is soft, use an alternate.",
        "settings": {"Texture": 25, "Clarity2012": 10, "Sharpness": 65},
    },
    "unknown": {
        "goal": "Keep the frame available for human review without overclaiming its role.",
        "style": "Natural, conservative correction only.",
        "reason": "The trainer could not confidently classify this frame, so Adobe MCP should keep it planned-only until resolved.",
        "preserve": "Original file, context, and any metadata needed for catalog resolution.",
        "beginner": "This photo needs a human or Adobe MCP catalog check before it becomes part of the final set.",
        "settings": {"Texture": 5, "Clarity2012": 0, "Sharpness": 35},
    },
}


def classify_role(focal_length: float | int | None) -> str:
    if focal_length is None:
        return "unknown"
    require_range(focal_length, 1, MAX_REVIEW_FOCAL_LENGTH_MM, "focal length")
    if focal_length <= 32:
        return "wide"
    if focal_length <= 42:
        return "massing"
    if focal_length <= 60:
        return "facade"
    return "tight"


def shot_number(item: dict[str, Any]) -> int:
    return int(item.get("plan", {}).get("shot") or item.get("trainer_shot") or 0)


def image_quality_score(item: dict[str, Any]) -> float:
    stats = item.get("image_analysis") or {}
    metadata = item.get("metadata") or {}
    score = 0.0

    if item.get("status") == "warn":
        score -= 8.0
    elif item.get("status") == "ok":
        score += 1.0

    tone = stats.get("tone")
    if tone == "balanced":
        score += 5.0
    elif tone == "flat":
        score += 2.0
    elif tone in {"bright", "dark"}:
        score -= 2.0

    contrast = stats.get("contrast")
    if contrast is not None:
        require_range(contrast, 0, MAX_REVIEW_CONTRAST, "contrast")
        if 120 <= contrast <= 220:
            score += 2.0
        elif contrast > 240:
            score -= 1.0

    highlight_clip = stats.get("highlight_clip_pct")
    if highlight_clip is not None:
        require_range(highlight_clip, 0, MAX_CLIP_PERCENT, "highlight clip percentage")
        score -= min(highlight_clip, 10.0) * 0.5

    shadow_clip = stats.get("shadow_clip_pct")
    if shadow_clip is not None:
        require_range(shadow_clip, 0, MAX_CLIP_PERCENT, "shadow clip percentage")
        score -= min(shadow_clip, 15.0) * 0.3

    if metadata.get("orientation") == "vertical":
        score += 1.0

    return round(score, 3)


def require_range(value: Any, minimum: float, maximum: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    try:
        numeric = float(value)
    except (OverflowError, TypeError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{label} must be a finite number")
    if not minimum <= numeric <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return numeric


def pick_spread(role_items: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    """Pick across the whole role pool instead of taking the earliest valid frames."""

    ordered = sorted(role_items, key=shot_number)
    if len(ordered) <= target:
        return ordered

    selected: list[dict[str, Any]] = []
    selected_shots: set[int] = set()
    count = len(ordered)
    for bucket_index in range(target):
        start = bucket_index * count // target
        end = (bucket_index + 1) * count // target
        bucket = ordered[start:end] or [ordered[min(start, count - 1)]]
        pick = max(bucket, key=lambda item: (image_quality_score(item), shot_number(item)))
        selected.append(pick)
        selected_shots.add(shot_number(pick))

    if len(selected_shots) < target:
        for item in sorted(
            ordered,
            key=lambda candidate: (
                min(abs(shot_number(candidate) - shot_number(pick)) for pick in selected),
                image_quality_score(candidate),
                shot_number(candidate),
            ),
            reverse=True,
        ):
            if shot_number(item) not in selected_shots:
                selected.append(item)
                selected_shots.add(shot_number(item))
            if len(selected_shots) == target:
                break

    return sorted(selected[:target], key=shot_number)


def recommended_set(reviewed: list[dict[str, Any]], role_targets: dict[str, int] | None = None) -> list[int]:
    targets = role_targets or ROLE_TARGETS
    selected: list[int] = []
    for role, target in targets.items():
        role_items = [
            item
            for item in reviewed
            if item.get("role") == role and item.get("status") in {"ok", "candidate"}
        ]
        selected.extend(shot_number(item) for item in pick_spread(role_items, target))
    return sorted(selected)


def build_adobe_mcp_handoff(
    review: dict[str, Any],
    *,
    slug: str,
    recommended_shots: list[int] | None = None,
    stale_recommended_sets: list[list[int]] | None = None,
) -> dict[str, Any]:
    items = list(review.get("items", []))
    selected = set(recommended_shots or recommended_set(items))
    photos = [handoff_photo(slug, item, shot_number(item) in selected) for item in items]
    recommended_photos = [photo for photo in photos if photo["recommended"]]
    return {
        "handoff_type": "28-75_trainer_to_adobe_mcp",
        "schema_version": "0.1",
        "status": "planned",
        "execution_boundary": {
            "trainer_role": "Coach and source of truth for selection, roles, visual intent, and learning signals.",
            "adobe_mcp_role": "Execution layer for catalog resolution, virtual copies, snapshots, write transactions, proof exports, QA, and run ledgers.",
            "lightroom_completion_claim_allowed": False,
            "completion_requires": ["Adobe MCP execution report", "proof export", "run ledger confirmation"],
        },
        "shoot": {
            "slug": slug,
            "source_report_json": review.get("source_report_json"),
            "source_report_html": review.get("source_report_html"),
            "photo_count": len(photos),
            "recommended_count": len(recommended_photos),
        },
        "selection": {
            "selection_method": "spread_selection_v1_with_exif_and_tone_hints",
            "stale_recommended_sets_to_ignore": stale_recommended_sets or [],
            "recommended_set": sorted(selected),
            "recommended_role_counts": dict(Counter(photo["role"] for photo in recommended_photos)),
        },
        "lightroom_develop_key_policy": {
            "allowed_keys_used": sorted(ALLOWED_DEVELOP_KEYS),
            "preview_only_or_risky": [
                "AI masks",
                "healing/generative remove",
                "local masks",
                "aggressive crop/transform",
                "deleting, moving, renaming, or overwriting originals",
            ],
        },
        "photos": photos,
    }


def handoff_photo(slug: str, item: dict[str, Any], recommended: bool) -> dict[str, Any]:
    shot = shot_number(item)
    metadata = item.get("metadata") or {}
    source_path = item.get("source") or item.get("path")
    exif_role = item.get("role") or classify_role(metadata.get("focal_length"))
    candidate_role = HANDOFF_ROLES.get(exif_role, "unknown")
    role = candidate_role if recommended else "alternate"
    photo = {
        "photo_id": stable_photo_id(slug, source_path, shot),
        "trainer_shot": shot,
        "recommended": recommended,
        "role": role,
        "alternate_candidate_role": None if recommended else candidate_role,
        "source_path": source_path,
        "filename": Path(source_path).name if source_path else metadata.get("filename"),
        "catalog_path": None,
        "uuid": None,
        "catalog_resolution_status": "unknown_adobe_mcp_required",
        "exif_hints": {
            "focal_length_mm": metadata.get("focal_length"),
            "timestamp": metadata.get("created"),
            "camera": metadata.get("camera"),
            "lens": metadata.get("lens"),
            "orientation": metadata.get("orientation"),
            "exposure_time": metadata.get("exposure_time"),
            "f_number": metadata.get("f_number"),
            "iso": metadata.get("iso"),
        },
        "warnings": list(item.get("warnings") or ([] if item.get("status") != "warn" else ["trainer_status_warn"])),
        "notes": list(item.get("notes") or []),
        "status": "planned",
    }
    if recommended:
        photo["edit_intent"] = edit_intent(role, item.get("image_analysis") or {})
    return photo


def stable_photo_id(slug: str, source_path: str | None, shot: int) -> str:
    name = Path(source_path).stem if source_path else f"shot-{shot:03d}"
    digest = hashlib.sha1(f"{slug}:{source_path}:{shot}".encode("utf-8")).hexdigest()[:10]
    return f"{slug}:shot-{shot:03d}:{name}:{digest}"


def edit_intent(role: str, image_analysis: dict[str, Any]) -> dict[str, Any]:
    profile = ROLE_EDIT_PROFILES[role]
    tone = image_analysis.get("tone") or "balanced"
    return {
        "status": "planned",
        "goal": profile["goal"],
        "style": profile["style"],
        "role_specific_reason": profile["reason"],
        "what_needs_fixing": needs_fixing(role, tone),
        "what_must_be_preserved": profile["preserve"],
        "risk_tags": ["non_destructive_only", "no_original_mutation", "transform_requires_dry_run"],
        "beginner_readable_explanation": profile["beginner"],
        "develop_settings_planned": develop_settings(role, tone),
        "preview_only_actions": [
            "AI masks",
            "healing/generative remove",
            "local masks",
            "aggressive crop/transform",
            "Auto Upright or Guided Upright before Adobe MCP dry-run proof",
        ],
    }


def needs_fixing(role: str, tone: str) -> list[str]:
    fixes = ["enable lens profile corrections", "remove chromatic aberration", "inspect verticals"]
    if tone == "bright":
        fixes.append("reduce highlights and whites to protect sunlit model surfaces")
    elif tone == "dark":
        fixes.append("lift exposure and shadows carefully without flattening contrast")
    else:
        fixes.append("keep exposure natural and protect bright sunlit areas")
    if role == "tight_detail_compression":
        fixes.append("verify focus at 100 percent before applying detail sharpening")
    return fixes


def develop_settings(role: str, tone: str) -> dict[str, Any]:
    settings: dict[str, Any] = {
        "EnableLensProfileCorrections": True,
        "RemoveChromaticAberration": True,
        "Contrast2012": 8,
        "Dehaze": 0,
        "Vibrance": 4,
        "Saturation": 0,
        "LuminanceSmoothing": 0,
        "CropAngle": 0,
        "PerspectiveHorizontal": 0,
        "PerspectiveVertical": 0,
    }
    settings.update(tone_settings(tone))
    settings.update(ROLE_EDIT_PROFILES[role]["settings"])
    unknown_keys = set(settings) - ALLOWED_DEVELOP_KEYS
    if unknown_keys:
        raise ValueError(f"Unsupported Lightroom develop keys: {sorted(unknown_keys)}")
    return settings


def tone_settings(tone: str) -> dict[str, float | int]:
    if tone == "dark":
        return {"Exposure2012": 0.25, "Highlights2012": -20, "Shadows2012": 30, "Whites2012": 0, "Blacks2012": 4}
    if tone == "bright":
        return {"Exposure2012": -0.25, "Highlights2012": -45, "Shadows2012": 10, "Whites2012": -20, "Blacks2012": -5}
    if tone == "flat":
        return {"Exposure2012": 0.0, "Highlights2012": -15, "Shadows2012": 10, "Whites2012": 10, "Blacks2012": -10}
    return {"Exposure2012": 0.0, "Highlights2012": -25, "Shadows2012": 15, "Whites2012": -10, "Blacks2012": -5}
