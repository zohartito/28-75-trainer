from __future__ import annotations

import csv
import io
import re
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
        lines.append(f"Source JSON: {markdown_code(source)}")
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
                "photo_id": spreadsheet_cell(photo_id(photo)),
                "trainer_shot": shot_number(photo),
                "filename": spreadsheet_cell(filename(photo)),
                "role": spreadsheet_cell(role(photo)),
                "setting_keys": spreadsheet_cell(";".join(setting_keys(photo))),
                "status": spreadsheet_cell(status(photo)),
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
        f"### Shot {shot_number(photo)} - {markdown_text(filename(photo))}",
        "",
        f"- Status: {markdown_text(status(photo))}",
        f"- Photo ID: {markdown_code(photo_id(photo))}",
    ]
    beginner = intent.get("beginner_readable_explanation")
    if beginner:
        lines.append(f"- Beginner read: {markdown_text(beginner)}")
    fixes = intent.get("what_needs_fixing") or []
    if fixes:
        lines.append("- Steps:")
        lines.extend(f"  - {markdown_text(fix)}" for fix in fixes)
    if keys:
        lines.append(f"- Setting keys: {', '.join(markdown_code(key) for key in keys)}")
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
    return markdown_text(role_name.replace("_", " ").title())


def nested_value(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def markdown_text(value: Any) -> str:
    """Render imported values as Markdown text, never markup or a link target."""

    text = normalize_markdown_inline(value)
    escaped = "".join("\\" + char if char in "`*_{}[]<>()#+!|" else char for char in text)
    # Escaping alone does not neutralize every block opener (notably '-' and
    # ordered-list markers).  Preserve imported text while ensuring it cannot
    # become the first token of a block when rendered in a field position.
    leading = escaped.lstrip(" \t")
    if leading.startswith(("-", "+")) or re.match(r"\d+[.)][ \t]", leading):
        prefix_length = len(escaped) - len(leading)
        escaped = escaped[:prefix_length] + "\\" + escaped[prefix_length:]
    return escaped


def markdown_code(value: Any) -> str:
    text = normalize_markdown_inline(value)
    longest_tick_run = max((len(match.group()) for match in re.finditer(r"`+", text)), default=0)
    # A code-span delimiter must be longer than any delimiter-like run in the
    # data. Padding avoids CommonMark's edge-space normalization ambiguity.
    fence = "`" * (longest_tick_run + 1)
    if "`" in text or text.startswith((" ", "`")) or text.endswith((" ", "`")):
        return f"{fence} {text} {fence}"
    return f"{fence}{text}{fence}"


def normalize_markdown_inline(value: Any) -> str:
    """Flatten every Unicode line separator before placing imported text inline."""

    return re.sub(r"[\r\n\v\f\x1c-\x1e\x85\u2028\u2029]+", " ", str(value)).replace("\\", "\\\\")


def spreadsheet_cell(value: Any) -> str:
    """Prevent a value imported by a spreadsheet from becoming a formula."""

    text = str(value)
    return "'" + text if text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")) else text
