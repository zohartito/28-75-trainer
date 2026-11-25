from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

from .reporting import write_text_output


def build_contact_sheet_html(
    reviewed: list[dict[str, Any]],
    *,
    recommended_shots: list[int] | set[int] | tuple[int, ...] | None = None,
    title: str = "28-75 Contact Sheet",
) -> str:
    selected = set(_recommended_shots_from_items(reviewed) if recommended_shots is None else recommended_shots)
    sanity = visual_selection_sanity(reviewed, recommended_shots=selected)
    rows = "\n".join(_contact_sheet_row(item, _shot_number(item) in selected) for item in sorted(reviewed, key=_shot_number))
    flags = ", ".join(sanity["flags"]) if sanity["flags"] else "none"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; vertical-align: top; }}
    th {{ background: #f5f5f5; }}
    .recommended {{ font-weight: 700; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <p>Selection sanity flags: {escape(flags)}</p>
  <table>
    <thead>
      <tr>
        <th>Filename</th>
        <th>Trainer Shot</th>
        <th>Role</th>
        <th>Focal Length</th>
        <th>Orientation</th>
        <th>Selection</th>
        <th>Status / Warnings</th>
        <th>Notes</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""


def write_contact_sheet_html(
    reviewed: list[dict[str, Any]],
    output_path: str | Path,
    *,
    recommended_shots: list[int] | set[int] | tuple[int, ...] | None = None,
    title: str = "28-75 Contact Sheet",
) -> Path:
    path = Path(output_path)
    html = build_contact_sheet_html(reviewed, recommended_shots=recommended_shots, title=title)
    write_text_output(path, html)
    return path


def visual_selection_sanity(
    reviewed: list[dict[str, Any]],
    *,
    recommended_shots: list[int] | set[int] | tuple[int, ...] | None = None,
    min_selected_count_for_cluster: int = 3,
    min_shot_span_ratio: float = 0.25,
) -> dict[str, Any]:
    selected = set(_recommended_shots_from_items(reviewed) if recommended_shots is None else recommended_shots)
    selected_items = [item for item in reviewed if _shot_number(item) in selected]
    all_shots = [_shot_number(item) for item in reviewed if _shot_number(item) > 0]
    selected_shots = sorted(_shot_number(item) for item in selected_items if _shot_number(item) > 0)
    flags: list[str] = []

    all_span = _shot_span(all_shots)
    selected_span = _shot_span(selected_shots)
    if (
        len(selected_shots) >= min_selected_count_for_cluster
        and all_span > 0
        and selected_span / all_span < min_shot_span_ratio
    ):
        flags.append("shot_cluster_too_narrow")

    duplicate_filenames = _duplicates(_filename(item) for item in selected_items)
    duplicate_source_paths = _duplicates(_source_path(item) for item in selected_items)
    if duplicate_filenames:
        flags.append("duplicate_filenames")
    if duplicate_source_paths:
        flags.append("duplicate_source_paths")

    return {
        "ok": not flags,
        "flags": flags,
        "selected_count": len(selected_items),
        "selected_shots": selected_shots,
        "selected_shot_span": selected_span,
        "reviewed_shot_span": all_span,
        "duplicate_filenames": duplicate_filenames,
        "duplicate_source_paths": duplicate_source_paths,
    }


def _contact_sheet_row(item: dict[str, Any], recommended: bool) -> str:
    selection = "Recommended" if recommended else "Alternate"
    selection_class = " class=\"recommended\"" if recommended else ""
    warnings = list(item.get("warnings") or [])
    status = item.get("status") or ""
    warning_status = " / ".join(str(value) for value in [status, *warnings] if value)
    notes = "; ".join(str(note) for note in item.get("notes") or [])
    return f"""      <tr{selection_class}>
        <td>{escape(_filename(item))}</td>
        <td>Shot {escape(str(_shot_number(item)))}</td>
        <td>{escape(str(item.get("role") or "unknown"))}</td>
        <td>{escape(_focal_length(item))}</td>
        <td>{escape(_orientation(item))}</td>
        <td>{selection}</td>
        <td>{escape(warning_status)}</td>
        <td>{escape(notes)}</td>
      </tr>"""


def _recommended_shots_from_items(reviewed: list[dict[str, Any]]) -> list[int]:
    return [_shot_number(item) for item in reviewed if item.get("recommended")]


def _shot_number(item: dict[str, Any]) -> int:
    return int(item.get("plan", {}).get("shot") or item.get("trainer_shot") or 0)


def _filename(item: dict[str, Any]) -> str:
    source_path = _source_path(item)
    metadata = item.get("metadata") or {}
    return str(item.get("filename") or metadata.get("filename") or (Path(source_path).name if source_path else "unknown"))


def _focal_length(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    exif_hints = item.get("exif_hints") or {}
    focal = metadata.get("focal_length") or metadata.get("focal_length_mm") or exif_hints.get("focal_length_mm")
    return f"{focal}mm" if focal is not None else "unknown"


def _orientation(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    exif_hints = item.get("exif_hints") or {}
    return str(metadata.get("orientation") or exif_hints.get("orientation") or "unknown")


def _source_path(item: dict[str, Any]) -> str:
    return str(item.get("source_path") or item.get("source") or item.get("path") or "")


def _shot_span(shots: list[int]) -> int:
    return max(shots) - min(shots) if shots else 0


def _duplicates(values: Any) -> list[str]:
    counted = Counter(value for value in values if value)
    return sorted(value for value, count in counted.items() if count > 1)
