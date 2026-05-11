from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analysis import analyze_folder
from .coaching import build_coaching_report
from .mission import DEFAULT_MISSION, mission_for_focus, mission_to_json, mission_to_markdown
from .reporting import (
    load_report_json,
    report_to_html,
    report_to_json,
    validate_review_output_locations,
    validate_distinct_output_paths,
    validate_report_regeneration_paths,
    write_text_output,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trainer2875",
        description="Local mission -> review folder -> coaching report loop for a 28-75mm zoom.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    mission_parser = subparsers.add_parser("mission", help="Print or write the next training mission.")
    mission_parser.add_argument("--focus", help="Optional focus area, such as wide, 28mm, tele, or 75mm.")
    mission_parser.add_argument("--json", action="store_true", help="Emit mission as JSON instead of Markdown.")
    mission_parser.add_argument("--out", help="Write mission to this path.")

    review_parser = subparsers.add_parser("review", help="Review a folder and generate coaching outputs.")
    review_parser.add_argument("folder", help="Folder containing images to review.")
    review_parser.add_argument("--focus", help="Optional mission focus, such as wide, 28mm, tele, or 75mm.")
    review_parser.add_argument("--out", default="reports/review.html", help="HTML report path.")
    review_parser.add_argument("--json-out", default="reports/review.json", help="JSON report path.")
    review_parser.add_argument("--json", action="store_true", help="Print the full coaching report JSON to stdout.")

    report_parser = subparsers.add_parser("report", help="Regenerate an HTML report from review JSON.")
    report_parser.add_argument("json_report", help="JSON report produced by the review command.")
    report_parser.add_argument("--out", default="reports/review.html", help="HTML report path.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "mission":
            return run_mission(args)
        if args.command == "review":
            return run_review(args)
        if args.command == "report":
            return run_report(args)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.error("Unknown command")
    return 2


def run_mission(args: argparse.Namespace) -> int:
    mission = mission_for_focus(args.focus)
    content = mission_to_json(mission) if args.json else mission_to_markdown(mission)
    if args.out:
        write_text_output(args.out, content)
        print(f"Wrote mission: {Path(args.out)}")
    else:
        print(content)
    return 0


def run_review(args: argparse.Namespace) -> int:
    mission = mission_for_focus(args.focus) if args.focus else DEFAULT_MISSION
    validate_distinct_output_paths(args.out, args.json_out)
    validate_review_output_locations(args.folder, args.out, args.json_out)
    analysis = analyze_folder(args.folder)
    report = build_coaching_report(analysis, mission)
    html_output = report_to_html(report)
    json_output = report_to_json(report)
    write_text_output(args.out, html_output)
    write_text_output(args.json_out, json_output)
    if args.json:
        print(json_output)
    else:
        print(f"Reviewed {len(analysis.photos)} recognized image file(s).")
        print(f"Wrote HTML report: {Path(args.out)}")
        print(f"Wrote JSON report: {Path(args.json_out)}")
        print(f"Next mission: {report.next_mission.title}")
    return 0


def run_report(args: argparse.Namespace) -> int:
    validate_report_regeneration_paths(args.json_report, args.out)
    data = load_report_json(args.json_report)
    write_text_output(args.out, report_to_html(data))
    print(f"Wrote HTML report: {Path(args.out)}")
    return 0
