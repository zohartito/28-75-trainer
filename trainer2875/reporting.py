from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .models import CoachingReport, REPORT_SCHEMA_VERSION, SUPPORTED_IMAGE_EXTENSIONS

COMPONENT_LABELS = {
    "volume": "Volume (supported files)",
    "focal_coverage": "Focal Coverage (filename tags)",
    "orientation_variety": "Orientation Variety (dimensions)",
    "selection_discipline": "Selection Discipline (exact hashes)",
    "metadata_completeness": "Metadata Completeness (dimensions + filename tags)",
}


def report_to_json(report: CoachingReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def load_report_json(path: str | Path) -> dict[str, Any]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_report_data(data)
    return data


def report_to_html(report: CoachingReport | dict[str, Any]) -> str:
    data = report.to_dict() if isinstance(report, CoachingReport) else report
    validate_report_data(data)
    mission = data["mission"]
    scorecard = data["scorecard"]
    analysis = data["analysis"]
    next_mission = data["next_mission"]
    coach_read = build_coach_read(data)
    rows = "\n".join(photo_row(photo) for photo in analysis["photos"])
    components = "\n".join(
        f"<tr><th>{escape(component_label(name))}</th><td>{escape(str(score))}</td></tr>"
        for name, score in scorecard["component_scores"].items()
    )
    observations = list_items(scorecard["observations"])
    recommendations = list_items(data["recommendations"])
    duplicates = duplicate_items(scorecard["duplicate_groups"])
    unsupported = list_items(analysis["unsupported_files"]) or "<p>None.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(mission["title"])} Review</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #202124;
      --muted: #5f6368;
      --line: #d8d9dc;
      --accent: #0f766e;
      --paper: #ffffff;
      --band: #f4f6f5;
    }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }}
    header, main {{
      max-width: 1040px;
      margin: 0 auto;
      padding: 24px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
    }}
    h1, h2 {{
      margin: 0 0 12px;
      letter-spacing: 0;
    }}
    h1 {{
      font-size: 32px;
    }}
    h2 {{
      margin-top: 28px;
      font-size: 21px;
    }}
    .score {{
      display: inline-block;
      padding: 8px 12px;
      background: var(--accent);
      color: white;
      font-weight: 700;
      border-radius: 4px;
    }}
    .muted {{
      color: var(--muted);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0 20px;
      font-size: 14px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: var(--band);
      font-weight: 700;
    }}
    code {{
      background: var(--band);
      padding: 2px 4px;
      border-radius: 3px;
    }}
    @media (max-width: 720px) {{
      header, main {{
        padding: 18px;
      }}
      table {{
        display: block;
        overflow-x: auto;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <p class="muted">28-75 Trainer v0.1</p>
    <h1>{escape(mission["title"])} Review</h1>
    <p>{escape(mission["objective"])}</p>
    <p><span class="score">Score {escape(str(scorecard["total_score"]))}/100</span></p>
  </header>
  <main>
    <h2>Coach Read</h2>
    <p>{escape(coach_read)}</p>
    <p class="muted">Evidence used in v0.1: filenames, dimensions, file hashes, and supported-file counts. This report does not judge sharpness, exposure, color, composition, or artistic quality yet.</p>

    <h2>Scorecard</h2>
    <table>
      <tbody>
        {components}
      </tbody>
    </table>

    <h2>Observations</h2>
    {observations}

    <h2>Coaching</h2>
    {recommendations}

    <h2>Reviewed Files</h2>
    <table>
      <thead>
        <tr>
          <th>File</th>
          <th>Filename Focal Tag</th>
          <th>Dimensions</th>
          <th>Orientation From Dimensions</th>
          <th>Megapixels</th>
          <th>Warnings</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>

    <h2>Exact File Duplicate Groups</h2>
    {duplicates}

    <h2>Unsupported Files</h2>
    {unsupported}

    <h2>Next Mission</h2>
    <p><strong>{escape(next_mission["title"])}</strong></p>
    <p>{escape(next_mission["objective"])}</p>
  </main>
</body>
</html>
"""


def photo_row(photo: dict[str, Any]) -> str:
    dims = "unknown"
    if photo.get("width") and photo.get("height"):
        dims = f"{photo['width']} x {photo['height']}"
    focal = f"{photo['focal_length_mm']}mm" if photo.get("focal_length_mm") else "unknown"
    warnings = ", ".join(photo.get("warnings", [])) or "none"
    megapixels = photo.get("megapixels")
    return (
        "<tr>"
        f"<td>{escape(photo['relative_path'])}</td>"
        f"<td>{escape(focal)}</td>"
        f"<td>{escape(dims)}</td>"
        f"<td>{escape(photo.get('orientation', 'unknown'))}</td>"
        f"<td>{escape(str(megapixels) if megapixels is not None else 'unknown')}</td>"
        f"<td>{escape(warnings)}</td>"
        "</tr>"
    )


def component_label(name: str) -> str:
    return COMPONENT_LABELS.get(name, name.replace("_", " ").title())


def sortable_score(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def build_coach_read(data: dict[str, Any]) -> str:
    scorecard = data["scorecard"]
    components = scorecard["component_scores"]
    total = scorecard["total_score"]
    weak = sorted(components.items(), key=lambda item: sortable_score(item[1]))
    weakest_name, weakest_score = weak[0] if weak else ("practice loop", total)
    mission_title = data["mission"]["title"]
    next_title = data["next_mission"]["title"]
    return (
        f"You ran the {mission_title} loop and scored {total}/100 on the evidence this tool can inspect today. "
        f"The best next improvement area is {component_label(weakest_name).lower()} at {weakest_score}/100. "
        f"The next suggested drill is {next_title}."
    )


def list_items(items: list[str] | tuple[str, ...]) -> str:
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def duplicate_items(groups: list[list[str]]) -> str:
    if not groups:
        return "<p>None.</p>"
    rendered = []
    for group in groups:
        rendered.append("<li>" + ", ".join(f"<code>{escape(path)}</code>" for path in group) + "</li>")
    return "<ul>" + "".join(rendered) + "</ul>"


def write_text_output(path: str | Path, content: str) -> None:
    output_path = validate_text_output_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def validate_text_output_path(path: str | Path) -> Path:
    output_path = Path(path).expanduser()
    if output_path.is_symlink():
        raise ValueError(f"Refusing to write report output through a symlink: {output_path}")
    for parent in output_path.parents:
        if parent.exists() and parent.is_symlink():
            raise ValueError(f"Refusing to write report output through a symlinked parent: {parent}")
    if output_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(f"Refusing to write report output to an image-like path: {output_path}")
    return output_path


def validate_distinct_output_paths(*paths: str | Path) -> None:
    for path in paths:
        validate_text_output_path(path)
    resolved = [Path(path).expanduser().resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Refusing to write multiple report outputs to the same path.")


def validate_report_regeneration_paths(json_report: str | Path, output: str | Path) -> None:
    validate_text_output_path(output)
    input_path = Path(json_report).expanduser().resolve()
    output_path = Path(output).expanduser().resolve()
    if input_path == output_path:
        raise ValueError("Refusing to overwrite the JSON report while regenerating HTML.")


def validate_review_output_locations(review_folder: str | Path, *outputs: str | Path) -> None:
    review_root = Path(review_folder).expanduser().resolve()
    for output in outputs:
        output_path = Path(output).expanduser().resolve()
        if output_path == review_root or review_root in output_path.parents:
            raise ValueError("Refusing to write review outputs inside the reviewed folder.")


def validate_report_data(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("Report JSON must be an object.")
    required = {
        "schema_version": str,
        "mission": dict,
        "analysis": dict,
        "scorecard": dict,
        "recommendations": list,
        "next_mission": dict,
    }
    for key, expected_type in required.items():
        if key not in data:
            raise ValueError(f"Report JSON is missing required field: {key}")
        if not isinstance(data[key], expected_type):
            raise ValueError(f"Report JSON field `{key}` has the wrong type.")
    if data["schema_version"] != REPORT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported report schema version: {data['schema_version']}")

    mission_required = ("title", "objective")
    for key in mission_required:
        if key not in data["mission"]:
            raise ValueError(f"Report JSON mission is missing required field: {key}")
    if "photos" not in data["analysis"] or not isinstance(data["analysis"]["photos"], list):
        raise ValueError("Report JSON analysis must include a photos list.")
    if "unsupported_files" not in data["analysis"] or not isinstance(data["analysis"]["unsupported_files"], list):
        raise ValueError("Report JSON analysis must include an unsupported_files list.")
    scorecard_required = {
        "total_score": (int, float, str),
        "component_scores": dict,
        "observations": list,
        "duplicate_groups": list,
    }
    for key, expected_type in scorecard_required.items():
        if key not in data["scorecard"]:
            raise ValueError(f"Report JSON scorecard is missing required field: {key}")
        if not isinstance(data["scorecard"][key], expected_type):
            raise ValueError(f"Report JSON scorecard field `{key}` has the wrong type.")
    for key in mission_required:
        if key not in data["next_mission"]:
            raise ValueError(f"Report JSON next_mission is missing required field: {key}")


def escape(value: str) -> str:
    return html.escape(value, quote=True)
