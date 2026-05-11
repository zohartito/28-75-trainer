from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .decision_buckets import build_decision_buckets, decision_items_by_shot
from .schema_versions import ADOBE_MCP_HANDOFF_SCHEMA_VERSION

ROLE_TARGETS = {"wide": 3, "massing": 3, "facade": 3, "tight": 3}
SIMILARITY_MAX_SHOT_GAP = 2
SIMILARITY_MIN_CONTRAST = 30.0
KEEPER_RECALL_SCHEMA_VERSION = "0.1"

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
    if isinstance(contrast, (int, float)):
        if 120 <= contrast <= 220:
            score += 2.0
        elif contrast > 240:
            score -= 1.0

    highlight_clip = stats.get("highlight_clip_pct")
    if isinstance(highlight_clip, (int, float)):
        score -= min(highlight_clip, 10.0) * 0.5

    shadow_clip = stats.get("shadow_clip_pct")
    if isinstance(shadow_clip, (int, float)):
        score -= min(shadow_clip, 15.0) * 0.3

    if metadata.get("orientation") == "vertical":
        score += 1.0

    return round(score, 3)


def annotate_similarity_groups(reviewed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assignments = similarity_group_assignments(reviewed)
    annotated: list[dict[str, Any]] = []
    for index, item in enumerate(reviewed):
        copy = dict(item)
        group_id = assignments.get(index)
        if group_id:
            copy["similarity_group_id"] = group_id
        else:
            copy.pop("similarity_group_id", None)
        annotated.append(copy)
    return annotated


def similarity_groups(reviewed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    annotated = annotate_similarity_groups(reviewed)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in annotated:
        group_id = item_similarity_group_id(item)
        if group_id:
            grouped[group_id].append(item)

    groups = []
    for group_id, items in grouped.items():
        if len(items) < 2:
            continue
        groups.append(
            {
                "similarity_group_id": group_id,
                "shots": sorted(shot_number(item) for item in items),
                "role": str(items[0].get("role") or "unknown"),
            }
        )
    return sorted(groups, key=lambda group: (min(group["shots"]), group["similarity_group_id"]))


def similarity_group_assignments(reviewed: list[dict[str, Any]]) -> dict[int, str]:
    assignments: dict[int, str] = {}
    used_ids: set[str] = set()
    for index, item in enumerate(reviewed):
        explicit = item_similarity_group_id(item)
        if explicit:
            assignments[index] = explicit
            used_ids.add(explicit)

    hash_counts = Counter(item_hash(item) for item in reviewed if item_hash(item))
    signature_items: dict[tuple[Any, ...], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, item in enumerate(reviewed):
        if index in assignments:
            continue
        sha = item_hash(item)
        if sha and hash_counts[sha] > 1:
            continue
        signature = similarity_signature(item)
        if signature is None:
            continue
        signature_items[signature].append((index, item))

    raw_groups: list[list[tuple[int, dict[str, Any]]]] = []
    for entries in signature_items.values():
        cluster: list[tuple[int, dict[str, Any]]] = []
        previous_shot: int | None = None
        for entry in sorted(entries, key=lambda value: (shot_number(value[1]), source_path(value[1]))):
            shot = shot_number(entry[1])
            if shot <= 0:
                flush_similarity_cluster(cluster, raw_groups)
                cluster = []
                previous_shot = None
                continue
            if previous_shot is None or shot - previous_shot <= SIMILARITY_MAX_SHOT_GAP:
                cluster.append(entry)
            else:
                flush_similarity_cluster(cluster, raw_groups)
                cluster = [entry]
            previous_shot = shot
        flush_similarity_cluster(cluster, raw_groups)

    raw_groups.sort(key=lambda group: (min(shot_number(item) for _, item in group), source_path(group[0][1])))
    next_id = 1
    for group in raw_groups:
        group_id = f"sim-{next_id:03d}"
        while group_id in used_ids:
            next_id += 1
            group_id = f"sim-{next_id:03d}"
        for index, _item in group:
            assignments[index] = group_id
        used_ids.add(group_id)
        next_id += 1
    return assignments


def flush_similarity_cluster(
    cluster: list[tuple[int, dict[str, Any]]],
    raw_groups: list[list[tuple[int, dict[str, Any]]]],
) -> None:
    if len(cluster) < 2:
        return
    hashes = [item_hash(item) for _, item in cluster]
    if all(hashes) and len(set(hashes)) == 1:
        return
    raw_groups.append(list(cluster))


def similarity_signature(item: dict[str, Any]) -> tuple[Any, ...] | None:
    if not has_similarity_evidence(item):
        return None

    metadata = item.get("metadata") or {}
    stats = item.get("image_analysis") or {}
    focal = numeric_value(
        metadata.get("focal_length")
        or metadata.get("focal_length_mm")
        or (item.get("exif_hints") or {}).get("focal_length_mm")
    )
    if focal is None:
        return None

    role = item.get("role") or classify_role(focal)
    if role not in ROLE_TARGETS:
        return None

    orientation = normalized_orientation(
        metadata.get("orientation") or (item.get("exif_hints") or {}).get("orientation")
    )
    if orientation == "unknown":
        orientation = orientation_from_dimensions(metadata.get("width"), metadata.get("height"))
    if orientation == "unknown":
        return None

    tone = stats.get("tone")
    if not tone:
        return None

    focal_bucket = int(round(focal / 2) * 2)
    return (role, focal_bucket, orientation, str(tone).lower())


def has_similarity_evidence(item: dict[str, Any]) -> bool:
    stats = item.get("image_analysis") or {}
    if stats.get("low_texture") is True:
        return False
    contrast = numeric_value(stats.get("contrast"))
    tone = str(stats.get("tone") or "").strip().lower()
    if tone == "flat" and contrast is None:
        return False
    if contrast is not None and contrast < SIMILARITY_MIN_CONTRAST:
        return False
    for key in ("edge_density", "texture_score", "detail_score"):
        value = numeric_value(stats.get(key))
        if value is not None and value < 0.05:
            return False
    return True


def item_similarity_group_id(item: dict[str, Any]) -> str | None:
    value = item.get("similarity_group_id") or item.get("similarity_group") or item.get("near_duplicate_group_id")
    return str(value) if value else None


def item_hash(item: dict[str, Any]) -> str | None:
    metadata = item.get("metadata") or {}
    value = item.get("sha256") or metadata.get("sha256")
    return str(value) if value else None


def source_path(item: dict[str, Any]) -> str:
    return str(item.get("source") or item.get("source_path") or item.get("path") or "")


def numeric_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().lower().removesuffix("mm")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def normalized_orientation(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"horizontal", "landscape"}:
        return "landscape"
    if text in {"vertical", "portrait"}:
        return "portrait"
    if text == "square":
        return "square"
    return "unknown"


def orientation_from_dimensions(width: Any, height: Any) -> str:
    numeric_width = numeric_value(width)
    numeric_height = numeric_value(height)
    if numeric_width is None or numeric_height is None:
        return "unknown"
    if numeric_width == numeric_height:
        return "square"
    if numeric_width > numeric_height:
        return "landscape"
    return "portrait"


def pick_spread(role_items: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    """Pick across the whole role pool instead of taking the earliest valid frames."""

    if target <= 0:
        return []

    ordered = sorted(role_items, key=shot_number)
    if len(ordered) <= target:
        return ordered

    diverse_pool = best_per_similarity_group(ordered)
    if len(diverse_pool) <= 1:
        return pick_spread_by_shot(ordered, target)
    if len(diverse_pool) >= target:
        return pick_spread_by_shot(diverse_pool, target)

    selected = pick_spread_by_shot(diverse_pool, len(diverse_pool))
    selected_shots = {shot_number(item) for item in selected}
    fill_pool = [item for item in ordered if shot_number(item) not in selected_shots]
    selected.extend(pick_spread_by_shot(fill_pool, target - len(selected)))
    return sorted(selected[:target], key=shot_number)


def best_per_similarity_group(role_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str | int], list[dict[str, Any]]] = defaultdict(list)
    for item in role_items:
        group_id = item_similarity_group_id(item)
        key = ("group", group_id) if group_id else ("shot", shot_number(item))
        buckets[key].append(item)
    representatives = [
        max(items, key=lambda item: (image_quality_score(item), shot_number(item))) for items in buckets.values()
    ]
    return sorted(representatives, key=shot_number)


def pick_spread_by_shot(role_items: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    ordered = sorted(role_items, key=shot_number)
    if target <= 0:
        return []
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
    annotated = annotate_similarity_groups(reviewed)
    selected: list[int] = []
    for role, target in targets.items():
        role_items = [
            item
            for item in annotated
            if item.get("role") == role and item.get("status") in {"ok", "candidate"}
        ]
        selected.extend(shot_number(item) for item in pick_spread(role_items, target))
    return sorted(selected)


def keeper_recall_benchmark(
    *,
    must_keep_photo_ids: list[str] | tuple[str, ...],
    recommended_photo_ids: list[str] | tuple[str, ...],
    all_photo_ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    must_keep = normalize_photo_ids(must_keep_photo_ids)
    recommended = set(normalize_photo_ids(recommended_photo_ids))
    all_ids = set(normalize_photo_ids(all_photo_ids or ()))
    known_must_keep = (
        must_keep
        if all_photo_ids is None
        else [photo_id for photo_id in must_keep if photo_id in all_ids]
    )
    unknown_must_keep = (
        []
        if all_photo_ids is None
        else [photo_id for photo_id in must_keep if photo_id not in all_ids]
    )
    false_rejected = [photo_id for photo_id in known_must_keep if photo_id not in recommended]
    false_reject_rate = round(len(false_rejected) / len(known_must_keep), 3) if known_must_keep else 0.0
    return {
        "schema_version": KEEPER_RECALL_SCHEMA_VERSION,
        "must_keep_count": len(known_must_keep),
        "recommended_must_keep_count": len(known_must_keep) - len(false_rejected),
        "false_reject_count": len(false_rejected),
        "false_rejected_photo_ids": false_rejected,
        "false_reject_rate": false_reject_rate,
        "false_reject_risk": "high" if false_rejected else "none",
        "override_count": len(false_rejected),
        "override_rate": false_reject_rate,
        "unknown_must_keep_photo_ids": unknown_must_keep,
    }


def normalize_photo_ids(photo_ids: list[str] | tuple[str, ...]) -> list[str]:
    normalized = set()
    for photo_id in photo_ids:
        if photo_id is None:
            continue
        value = str(photo_id).strip()
        if value:
            normalized.add(value)
    return sorted(normalized)


def build_adobe_mcp_handoff(
    review: dict[str, Any],
    *,
    slug: str,
    recommended_shots: list[int] | None = None,
    stale_recommended_sets: list[list[int]] | None = None,
    must_keep_photo_ids: list[str] | None = None,
) -> dict[str, Any]:
    items = annotate_similarity_groups(list(review.get("items", [])))
    groups = similarity_groups(items)
    selected = set(recommended_shots or recommended_set(items))
    decision_buckets = build_decision_buckets(
        items,
        selected_shots=selected,
        overrides=review.get("decision_overrides") or review.get("overrides"),
        coach_preferences=review.get("coach_preferences"),
    )
    decision_by_shot = decision_items_by_shot(decision_buckets)
    photos = [
        handoff_photo(slug, item, shot_number(item) in selected, decision_by_shot.get(shot_number(item)))
        for item in items
    ]
    recommended_photos = [photo for photo in photos if photo["recommended"]]
    selection = {
        "selection_method": "spread_selection_v2_with_exif_tone_and_similarity_groups",
        "stale_recommended_sets_to_ignore": stale_recommended_sets or [],
        "recommended_set": sorted(selected),
        "recommended_role_counts": dict(Counter(photo["role"] for photo in recommended_photos)),
        "similarity_groups": groups,
    }
    if must_keep_photo_ids is not None:
        selection["keeper_recall"] = keeper_recall_benchmark(
            must_keep_photo_ids=must_keep_photo_ids,
            recommended_photo_ids=[photo["photo_id"] for photo in recommended_photos],
            all_photo_ids=[photo["photo_id"] for photo in photos],
        )
    return {
        "handoff_type": "28-75_trainer_to_adobe_mcp",
        "schema_version": ADOBE_MCP_HANDOFF_SCHEMA_VERSION,
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
        "selection": selection,
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
        "decision_buckets": decision_buckets,
        "photos": photos,
    }


def handoff_photo(
    slug: str,
    item: dict[str, Any],
    recommended: bool,
    decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "similarity_group_id": item_similarity_group_id(item),
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
        "decision_bucket": decision.get("bucket") if decision else None,
        "deterministic_decision_bucket": decision.get("deterministic_bucket") if decision else None,
        "decision_reasons": list(decision.get("reasons") or []) if decision else [],
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
