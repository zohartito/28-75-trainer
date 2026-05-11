from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

BUCKET_SCHEMA_VERSION = "0.1"
BUCKET_NAMES = ("select", "maybe", "reject", "practice-evidence")
DETERMINISTIC_REASON_SOURCES = ("deterministic", "metadata")
HUMAN_REASON_SOURCES = ("coach_preference", "user_override")

ELIGIBLE_STATUSES = {"", "ok", "candidate"}
REJECT_STATUSES = {"reject", "rejected", "failed", "error", "unsupported"}
PRACTICE_EVIDENCE_STATUSES = {
    "warn",
    "warning",
    "needs_review",
    "needs-review",
    "practice-evidence",
    "practice_evidence",
}


def build_decision_buckets(
    items: Iterable[dict[str, Any]],
    *,
    selected_shots: Iterable[int] | None = None,
    overrides: Mapping[int | str, str | Mapping[str, Any]] | Iterable[Mapping[str, Any]] | None = None,
    coach_preferences: Mapping[int | str, str | Iterable[str]] | None = None,
) -> dict[str, Any]:
    """Build source-labeled decision buckets without mutating source items."""

    item_list = list(items)
    selected = (
        {int(shot) for shot in selected_shots}
        if selected_shots is not None
        else {shot_number(item) for item in item_list if item.get("recommended") is True}
    )
    override_by_shot = normalize_overrides(overrides)
    coach_reasons_by_shot = normalize_coach_preferences(coach_preferences)
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in BUCKET_NAMES}

    for item in sorted(item_list, key=shot_number):
        shot = shot_number(item)
        deterministic_bucket = bucket_for_item(item, selected_shots=selected)
        override = override_by_shot.get(shot)
        bucket = str(override["bucket"]) if override else deterministic_bucket
        validate_bucket(bucket)

        reasons = bucket_reasons(item, deterministic_bucket, selected_shots=selected)
        reasons.extend(coach_reasons_by_shot.get(shot, []))
        if override:
            reasons.append(
                reason(
                    "user_override",
                    "bucket_override",
                    str(override.get("reason") or f"User override moved this item to {bucket}."),
                )
            )

        bucket_item = {
            "trainer_shot": shot,
            "bucket": bucket,
            "deterministic_bucket": deterministic_bucket,
            "filename": filename(item),
            "source_path": source_path(item),
            "role": str(item.get("role") or "unknown"),
            "status": str(item.get("status") or "unknown"),
            "reasons": reasons,
        }
        buckets[bucket].append(bucket_item)

    return {
        "schema_version": BUCKET_SCHEMA_VERSION,
        "bucket_names": list(BUCKET_NAMES),
        "reason_source_groups": {
            "deterministic_evidence": list(DETERMINISTIC_REASON_SOURCES),
            "human_or_coach_preference": list(HUMAN_REASON_SOURCES),
        },
        "counts": {name: len(buckets[name]) for name in BUCKET_NAMES},
        "buckets": buckets,
    }


def decision_items_by_shot(decision_buckets: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    items: dict[int, dict[str, Any]] = {}
    for bucket_items in (decision_buckets.get("buckets") or {}).values():
        for item in bucket_items:
            items[int(item.get("trainer_shot") or 0)] = item
    return items


def bucket_for_item(item: Mapping[str, Any], *, selected_shots: set[int]) -> str:
    if shot_number(item) in selected_shots:
        return "select"

    status = normalized_status(item)
    if status in REJECT_STATUSES:
        return "reject"
    if status in PRACTICE_EVIDENCE_STATUSES or item.get("warnings"):
        return "practice-evidence"
    if str(item.get("role") or "").lower() in {"", "unknown"}:
        return "practice-evidence"
    if status in ELIGIBLE_STATUSES:
        return "maybe"
    return "practice-evidence"


def bucket_reasons(
    item: Mapping[str, Any],
    deterministic_bucket: str,
    *,
    selected_shots: set[int],
) -> list[dict[str, str]]:
    if deterministic_bucket == "select":
        deterministic_text = (
            "Shot is in the deterministic selected set for this review; this is a recommendation, not an artistic certainty."
        )
        deterministic_code = "selected_set"
    elif deterministic_bucket == "maybe":
        deterministic_text = (
            "Shot is eligible review material but is not in the deterministic selected set for this round."
        )
        deterministic_code = "eligible_alternate"
    elif deterministic_bucket == "reject":
        deterministic_text = "Shot is excluded by deterministic review status rather than aesthetic judgment."
        deterministic_code = "excluded_status"
    else:
        deterministic_text = (
            "Shot is held as practice evidence because metadata, status, or warnings need human review."
        )
        deterministic_code = "practice_evidence"

    return [
        reason("deterministic", deterministic_code, deterministic_text),
        reason("metadata", "item_metadata", metadata_summary(item, selected_shots=selected_shots)),
    ]


def metadata_summary(item: Mapping[str, Any], *, selected_shots: set[int]) -> str:
    metadata = item.get("metadata") or {}
    focal = metadata.get("focal_length") or metadata.get("focal_length_mm")
    exif_hints = item.get("exif_hints") or {}
    focal = focal if focal is not None else exif_hints.get("focal_length_mm")
    focal_text = f"{focal}mm" if focal is not None else "unknown focal length"
    selected_text = "selected" if shot_number(item) in selected_shots else "not selected"
    warnings = item.get("warnings") or []
    warning_text = f"; warnings: {', '.join(str(warning) for warning in warnings)}" if warnings else ""
    return (
        f"Trainer metadata says status {normalized_status(item) or 'unknown'}, "
        f"role {item.get('role') or 'unknown'}, {focal_text}, {selected_text}{warning_text}."
    )


def normalize_overrides(
    overrides: Mapping[int | str, str | Mapping[str, Any]] | Iterable[Mapping[str, Any]] | None,
) -> dict[int, dict[str, Any]]:
    if not overrides:
        return {}

    normalized: dict[int, dict[str, Any]] = {}
    if isinstance(overrides, Mapping):
        for shot, value in overrides.items():
            override = {"bucket": value} if isinstance(value, str) else dict(value)
            override["trainer_shot"] = int(shot)
            validate_bucket(str(override.get("bucket")))
            normalized[int(shot)] = override
        return normalized

    for value in overrides:
        override = dict(value)
        shot = int(override.get("trainer_shot") or override.get("shot") or 0)
        if shot <= 0:
            raise ValueError("Decision bucket override is missing trainer_shot.")
        validate_bucket(str(override.get("bucket")))
        normalized[shot] = override
    return normalized


def normalize_coach_preferences(
    coach_preferences: Mapping[int | str, str | Iterable[str]] | None,
) -> dict[int, list[dict[str, str]]]:
    if not coach_preferences:
        return {}
    normalized: dict[int, list[dict[str, str]]] = {}
    for shot, value in coach_preferences.items():
        values = [value] if isinstance(value, str) else list(value)
        normalized[int(shot)] = [
            reason("coach_preference", "coach_note", str(text))
            for text in values
            if str(text).strip()
        ]
    return normalized


def reason(source: str, code: str, text: str) -> dict[str, str]:
    return {"source": source, "code": code, "text": text}


def validate_bucket(bucket: str) -> None:
    if bucket not in BUCKET_NAMES:
        raise ValueError(f"Unsupported decision bucket: {bucket}")


def normalized_status(item: Mapping[str, Any]) -> str:
    return str(item.get("status") or "").strip().lower()


def shot_number(item: Mapping[str, Any]) -> int:
    return int((item.get("plan") or {}).get("shot") or item.get("trainer_shot") or 0)


def filename(item: Mapping[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    value = item.get("filename") or metadata.get("filename")
    if value:
        return str(value)
    source = source_path(item)
    return Path(source).name if source else f"shot-{shot_number(item):03d}"


def source_path(item: Mapping[str, Any]) -> str:
    return str(item.get("source_path") or item.get("source") or item.get("path") or "")
