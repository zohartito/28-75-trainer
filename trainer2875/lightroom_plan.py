from __future__ import annotations

import csv
import io
from collections import defaultdict
from pathlib import Path
from typing import Any

CSV_FIELDS = ["photo_id", "trainer_shot", "filename", "role", "setting_keys", "status"]

ROLE_ORDER = {
    "wide_context": 0,
    "wide": 0,
    "massing_medium": 1,
    "massing": 1,
    "facade_detail_context": 2,
    "facade": 2,
    "tight_detail_compression": 3,
    "tight": 3,
}


def lightroom_plan_to_markdown(plan_source: dict[str, Any], *, source_json_path: str | Path | None = None) -> str:
    photos = recommended_photos(plan_source)
    recommended = recommended_set(plan_source, photos)
    source = source_json_path or nested_value(plan_source, ("shoot", "source_report_json")) or plan_source.get("source_report_json")
    lines = [
        "# Lightroom Classic Fix Sheet",
        "",
        "This is a planned-only fix sheet for Lightroom Classic. No edits have been applied by 28-75 Trainer.",
        "Use these steps manually or hand them to a separate execution layer only after review.",
        "",
    ]
    if source:
        lines.append(f"Source JSON: `{source}`")
    else:
        lines.append("Source JSON: not supplied")
    lines.extend(
        [
            f"Recommended set: {', '.join(str(shot) for shot in recommended) if recommended else 'none'}",
            "",
            "Boundary: 28-75 Trainer describes selection, role, intent, and planned setting keys only. Lightroom Classic execution, catalog resolution, exports, and proof checks happen outside this exporter.",
            "",
        ]
    )

    for role, role_photos in grouped_by_role(photos):
        lines.extend([f"## Role: {role_label(role)}", ""])
        for photo in role_photos:
            lines.extend(photo_markdown(photo))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def lightroom_plan_to_csv(plan_source: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for photo in recommended_photos(plan_source):
        writer.writerow(
            {
                "photo_id": photo_id(photo),
                "trainer_shot": shot_number(photo),
                "filename": filename(photo),
                "role": role(photo),
                "setting_keys": ";".join(setting_keys(photo)),
                "status": status(photo),
            }
        )
    return output.getvalue()


def recommended_photos(plan_source: dict[str, Any]) -> list[dict[str, Any]]:
    photos = list(plan_source.get("photos") or plan_source.get("items") or [])
    selected = set(recommended_set(plan_source, photos))
    recommended = [
        photo
        for photo in photos
        if photo.get("recommended") is True or (selected and shot_number(photo) in selected)
    ]
    return sorted(recommended, key=photo_sort_key)


def recommended_set(plan_source: dict[str, Any], photos: list[dict[str, Any]]) -> list[int]:
    explicit = nested_value(plan_source, ("selection", "recommended_set")) or plan_source.get("recommended_set")
    if explicit:
        return sorted(int(shot) for shot in explicit)
    return sorted(shot_number(photo) for photo in photos if photo.get("recommended") is True)


def grouped_by_role(photos: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for photo in photos:
        groups[role(photo)].append(photo)
    return sorted(
        ((role_name, sorted(role_photos, key=photo_sort_key)) for role_name, role_photos in groups.items()),
        key=lambda item: (ROLE_ORDER.get(item[0], 99), item[0]),
    )


def photo_markdown(photo: dict[str, Any]) -> list[str]:
    intent = photo.get("edit_intent") or {}
    keys = setting_keys(photo)
    lines = [
        f"### Shot {shot_number(photo)} - {filename(photo)}",
        "",
        f"- Status: {status(photo)}",
        f"- Photo ID: `{photo_id(photo)}`",
    ]
    beginner = intent.get("beginner_readable_explanation")
    if beginner:
        lines.append(f"- Beginner read: {beginner}")
    fixes = intent.get("what_needs_fixing") or []
    if fixes:
        lines.append("- Steps:")
        lines.extend(f"  - {fix}" for fix in fixes)
    if keys:
        lines.append(f"- Setting keys: {', '.join(f'`{key}`' for key in keys)}")
    else:
        lines.append("- Setting keys: none supplied")
    return lines


def photo_sort_key(photo: dict[str, Any]) -> tuple[int, int, str, str]:
    return (ROLE_ORDER.get(role(photo), 99), shot_number(photo), filename(photo), photo_id(photo))


def setting_keys(photo: dict[str, Any]) -> list[str]:
    settings = (photo.get("edit_intent") or {}).get("develop_settings_planned") or {}
    return sorted(str(key) for key in settings)


def status(photo: dict[str, Any]) -> str:
    intent = photo.get("edit_intent") or {}
    return str(intent.get("status") or photo.get("status") or "planned")


def photo_id(photo: dict[str, Any]) -> str:
    value = photo.get("photo_id")
    if value:
        return str(value)
    return f"shot-{shot_number(photo):03d}"


def shot_number(photo: dict[str, Any]) -> int:
    raw = photo.get("trainer_shot") or nested_value(photo, ("plan", "shot")) or 0
    return int(raw)


def filename(photo: dict[str, Any]) -> str:
    value = photo.get("filename")
    if value:
        return str(value)
    source = photo.get("source_path") or photo.get("source") or photo.get("path")
    return Path(source).name if source else f"shot-{shot_number(photo):03d}"


def role(photo: dict[str, Any]) -> str:
    return str(photo.get("role") or "unknown")


def role_label(role_name: str) -> str:
    return role_name.replace("_", " ").title()


def nested_value(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
