from __future__ import annotations

import os
import shutil
from collections import Counter
from collections.abc import Mapping
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .decision_buckets import build_decision_buckets, decision_items_by_shot
from .field_review import annotate_similarity_groups, item_similarity_group_id
from .schema_versions import CONTACT_SHEET_SCHEMA_VERSIONS, validate_schema_version

ContactSheetData = list[dict[str, Any]] | Mapping[str, Any]


def build_contact_sheet_html(
    reviewed: ContactSheetData,
    *,
    recommended_shots: list[int] | set[int] | tuple[int, ...] | None = None,
    title: str = "28-75 Contact Sheet",
    source_root: str | Path | None = None,
) -> str:
    return _build_contact_sheet_html(
        reviewed,
        recommended_shots=recommended_shots,
        title=title,
        source_root=source_root,
    )


def _build_contact_sheet_html(
    reviewed: ContactSheetData,
    *,
    recommended_shots: list[int] | set[int] | tuple[int, ...] | None = None,
    title: str = "28-75 Contact Sheet",
    source_root: str | Path | None = None,
    output_path: str | Path | None = None,
    preview_refs: dict[int, str] | None = None,
) -> str:
    items = contact_sheet_items(reviewed)
    annotated = annotate_similarity_groups(items)
    selected = set(recommended_shots or _recommended_shots_from_items(annotated))
    decisions = contact_sheet_decision_buckets(reviewed, annotated, selected)
    decision_by_shot = decision_items_by_shot(decisions)
    sanity = visual_selection_sanity(annotated, recommended_shots=selected)
    ordered = sorted(annotated, key=_shot_number)
    show_similarity_group = any(_similarity_group(item) is not None for item in ordered)
    rows = "\n".join(
        _contact_sheet_row(
            item,
            _shot_number(item) in selected,
            decision_by_shot.get(_shot_number(item)),
            source_root=source_root,
            output_path=output_path,
            preview_ref=(preview_refs or {}).get(_shot_number(item)),
            show_similarity_group=show_similarity_group,
        )
        for item in ordered
    )
    flags = ", ".join(sanity["flags"]) if sanity["flags"] else "none"
    similarity_header = "\n        <th>Similarity Group</th>" if show_similarity_group else ""
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
    .preview img {{ display: block; max-width: 160px; max-height: 120px; object-fit: contain; }}
    .preview-missing {{ color: #666; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <p>Selection sanity flags: {escape(flags)}</p>
  <table>
    <thead>
      <tr>
        <th>Preview</th>
        <th>Filename</th>
        <th>Trainer Shot</th>
        <th>Role</th>
        <th>Focal Length</th>
        <th>Orientation</th>
        <th>Pick State</th>{similarity_header}
        <th>Decision Bucket</th>
        <th>Decision Reasons</th>
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
    reviewed: ContactSheetData,
    output_path: str | Path,
    *,
    recommended_shots: list[int] | set[int] | tuple[int, ...] | None = None,
    title: str = "28-75 Contact Sheet",
    source_root: str | Path | None = None,
    preview_assets_dir: str | Path | None = None,
) -> Path:
    path = Path(output_path)
    items = contact_sheet_items(reviewed)
    validate_contact_sheet_output_path(path, items, source_root=source_root)
    preview_refs = (
        _copy_preview_assets(items, preview_assets_dir, output_path=path, source_root=source_root)
        if preview_assets_dir is not None
        else None
    )
    html = _build_contact_sheet_html(
        reviewed,
        recommended_shots=recommended_shots,
        title=title,
        source_root=source_root,
        output_path=path,
        preview_refs=preview_refs,
    )
    path.write_text(html, encoding="utf-8")
    return path


def visual_selection_sanity(
    reviewed: ContactSheetData,
    *,
    recommended_shots: list[int] | set[int] | tuple[int, ...] | None = None,
    min_selected_count_for_cluster: int = 3,
    min_shot_span_ratio: float = 0.25,
) -> dict[str, Any]:
    items = contact_sheet_items(reviewed)
    annotated = annotate_similarity_groups(items)
    selected = set(recommended_shots or _recommended_shots_from_items(annotated))
    selected_items = [item for item in annotated if _shot_number(item) in selected]
    all_shots = [_shot_number(item) for item in annotated if _shot_number(item) > 0]
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
    repeated_similarity_groups = _duplicates(item_similarity_group_id(item) for item in selected_items)
    if duplicate_filenames:
        flags.append("duplicate_filenames")
    if duplicate_source_paths:
        flags.append("duplicate_source_paths")
    if repeated_similarity_groups:
        flags.append("similarity_group_repeated")

    return {
        "ok": not flags,
        "flags": flags,
        "selected_count": len(selected_items),
        "selected_shots": selected_shots,
        "selected_shot_span": selected_span,
        "reviewed_shot_span": all_span,
        "duplicate_filenames": duplicate_filenames,
        "duplicate_source_paths": duplicate_source_paths,
        "repeated_similarity_groups": repeated_similarity_groups,
    }


def contact_sheet_items(reviewed: ContactSheetData) -> list[dict[str, Any]]:
    if isinstance(reviewed, Mapping):
        validate_schema_version(
            reviewed,
            artifact="contact sheet",
            supported_versions=CONTACT_SHEET_SCHEMA_VERSIONS,
        )
        items = reviewed.get("items")
        if not isinstance(items, list):
            raise ValueError("Contact sheet data field `items` must be a list.")
        return items
    if not isinstance(reviewed, list):
        raise ValueError("Contact sheet data must be a list or an object.")
    return reviewed


def contact_sheet_decision_buckets(
    reviewed: ContactSheetData,
    items: list[dict[str, Any]],
    selected: set[int],
) -> dict[str, Any]:
    if isinstance(reviewed, Mapping):
        existing = reviewed.get("decision_buckets")
        if isinstance(existing, Mapping):
            return dict(existing)
        return build_decision_buckets(
            items,
            selected_shots=selected,
            overrides=reviewed.get("decision_overrides") or reviewed.get("overrides"),
            coach_preferences=reviewed.get("coach_preferences"),
        )
    return build_decision_buckets(items, selected_shots=selected)


def validate_contact_sheet_output_path(
    output_path: Path,
    items: list[dict[str, Any]],
    *,
    source_root: str | Path | None = None,
) -> None:
    output_resolved = output_path.expanduser().resolve()
    for item in items:
        source = _resolve_local_source(item, source_root=source_root)
        if source is not None and source.resolve() == output_resolved:
            raise ValueError("Refusing to overwrite an original image with a contact sheet report.")


def _contact_sheet_row(
    item: dict[str, Any],
    recommended: bool,
    decision: dict[str, Any] | None,
    *,
    source_root: str | Path | None = None,
    output_path: str | Path | None = None,
    preview_ref: str | None = None,
    show_similarity_group: bool = False,
) -> str:
    selection = "Recommended" if recommended else "Alternate"
    selection_class = " class=\"recommended\"" if recommended else ""
    warnings = list(item.get("warnings") or [])
    status = item.get("status") or ""
    warning_status = " / ".join(str(value) for value in [status, *warnings] if value)
    notes = "; ".join(str(note) for note in item.get("notes") or [])
    decision_bucket = decision.get("bucket") if decision else ""
    decision_reasons = _decision_reasons(decision)
    preview = preview_ref or _local_preview_reference(item, source_root=source_root, output_path=output_path)
    similarity_cell = f"\n        <td>{escape(_similarity_group(item) or '')}</td>" if show_similarity_group else ""
    return f"""      <tr{selection_class}>
        <td class="preview">{_preview_html(item, preview)}</td>
        <td>{escape(_filename(item))}</td>
        <td>Shot {escape(str(_shot_number(item)))}</td>
        <td>{escape(str(item.get("role") or "unknown"))}</td>
        <td>{escape(_focal_length(item))}</td>
        <td>{escape(_orientation(item))}</td>
        <td>{selection}</td>{similarity_cell}
        <td>{escape(str(decision_bucket))}</td>
        <td>{escape(decision_reasons)}</td>
        <td>{escape(warning_status)}</td>
        <td>{escape(notes)}</td>
      </tr>"""


def _decision_reasons(decision: dict[str, Any] | None) -> str:
    if not decision:
        return ""
    return "; ".join(
        f"{reason.get('source')}: {reason.get('text')}"
        for reason in decision.get("reasons") or []
        if reason.get("source") and reason.get("text")
    )


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


def _similarity_group(item: dict[str, Any]) -> str | None:
    for key in ("similarity_group", "similarity_group_id", "similarity_cluster", "similarity_cluster_id"):
        if item.get(key) not in (None, ""):
            return str(item[key])
    for parent_key in ("similarity", "image_analysis"):
        parent = item.get(parent_key)
        if not isinstance(parent, dict):
            continue
        for key in ("group", "group_id", "similarity_group", "similarity_group_id", "cluster", "cluster_id"):
            if parent.get(key) not in (None, ""):
                return str(parent[key])
    return None


def _preview_html(item: dict[str, Any], preview_ref: str | None) -> str:
    if not preview_ref:
        return '<span class="preview-missing">No local preview</span>'
    safe_ref = escape(preview_ref, quote=True)
    alt = escape(_filename(item), quote=True)
    return f'<a href="{safe_ref}"><img src="{safe_ref}" alt="{alt}" loading="lazy"></a>'


def _local_preview_reference(
    item: dict[str, Any],
    *,
    source_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> str | None:
    path = _resolve_local_source(item, source_root=source_root)
    if path is None:
        return None
    return _href_for_local_path(path, output_path=output_path)


def _resolve_local_source(item: dict[str, Any], *, source_root: str | Path | None = None) -> Path | None:
    raw = _source_path(item).strip()
    if not raw or _is_nonlocal_asset(raw):
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute() and source_root is not None:
        path = Path(source_root).expanduser() / path
    try:
        resolved = path.resolve()
    except OSError:
        return None
    if not resolved.is_file():
        return None
    return resolved


def _is_nonlocal_asset(source: str) -> bool:
    normalized = source.strip().lower()
    return normalized.startswith(("http://", "https://", "ftp://", "data:", "//", "\\\\"))


def _copy_preview_assets(
    reviewed: list[dict[str, Any]],
    preview_assets_dir: str | Path,
    *,
    output_path: str | Path,
    source_root: str | Path | None = None,
) -> dict[int, str]:
    # The Python standard library cannot safely resize raster images here; this creates
    # local preview copies and lets the browser scale them in the contact sheet.
    sources = [
        (item, source)
        for item in reviewed
        for source in [_resolve_local_source(item, source_root=source_root)]
        if source is not None
    ]
    assets_dir = Path(preview_assets_dir).expanduser()
    _validate_preview_assets_dir(assets_dir, [source for _, source in sources])
    assets_dir.mkdir(parents=True, exist_ok=True)

    refs: dict[int, str] = {}
    used_names: set[str] = set()
    for item, source in sorted(sources, key=lambda pair: _shot_number(pair[0])):
        target = assets_dir / _preview_asset_filename(item, source, used_names)
        if target.resolve() == source.resolve():
            raise ValueError("Refusing to overwrite an original image while creating contact sheet previews.")
        shutil.copyfile(source, target)
        refs[_shot_number(item)] = _href_for_local_path(target, output_path=output_path)
    return refs


def _validate_preview_assets_dir(assets_dir: Path, sources: list[Path]) -> None:
    assets_resolved = assets_dir.resolve()
    for source in sources:
        source_parent = source.resolve().parent
        if assets_resolved == source_parent or source_parent in assets_resolved.parents:
            raise ValueError("Refusing to write contact sheet preview assets inside an original source folder.")


def _preview_asset_filename(item: dict[str, Any], source: Path, used_names: set[str]) -> str:
    shot = _shot_number(item)
    stem = _safe_asset_stem(source.stem or Path(_filename(item)).stem)
    suffix = source.suffix.lower() or ".img"
    name = f"shot-{shot:03d}-{stem}{suffix}"
    candidate = name
    index = 2
    while candidate.lower() in used_names:
        candidate = f"shot-{shot:03d}-{stem}-{index}{suffix}"
        index += 1
    used_names.add(candidate.lower())
    return candidate


def _safe_asset_stem(value: str) -> str:
    stem = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value.strip())
    while "--" in stem:
        stem = stem.replace("--", "-")
    return stem.strip("-") or "preview"


def _href_for_local_path(path: Path, *, output_path: str | Path | None = None) -> str:
    resolved = path.expanduser().resolve()
    if output_path is not None:
        try:
            relative = os.path.relpath(resolved, Path(output_path).expanduser().resolve().parent)
        except ValueError:
            return resolved.as_uri()
        return quote(Path(relative).as_posix(), safe="/")
    return resolved.as_uri()


def _shot_span(shots: list[int]) -> int:
    return max(shots) - min(shots) if shots else 0


def _duplicates(values: Any) -> list[str]:
    counted = Counter(value for value in values if value)
    return sorted(value for value, count in counted.items() if count > 1)
