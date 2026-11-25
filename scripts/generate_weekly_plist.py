from __future__ import annotations

import argparse
import plistlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from trainer2875.reporting import write_text_output
from trainer2875.safeio import OutputDirectory, absolute_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a weekly launchd plist without loading it.")
    parser.add_argument("output", help="Destination plist path.")
    parser.add_argument("--repo", default=str(REPO_ROOT), help="Clone to schedule (default: this checkout).")
    parser.add_argument("--python", default=sys.executable, help="Absolute Python 3.10+ interpreter path.")
    args = parser.parse_args(argv)
    repo = absolute_path(args.repo)
    interpreter = absolute_path(args.python)
    script = repo / "scripts" / "weekly_progress.py"
    if not script.is_file() or not interpreter.is_file():
        parser.error("The selected clone must contain scripts/weekly_progress.py and the interpreter must exist.")
    template = REPO_ROOT / "launchd" / "com.zohar.trainer2875-weekly.plist.in"
    config = plistlib.loads(template.read_bytes())
    config["ProgramArguments"] = [str(interpreter), str(script)]
    config["WorkingDirectory"] = str(repo)
    log_dir = repo / "state"
    with OutputDirectory(log_dir):
        pass
    config["StandardOutPath"] = config["StandardErrorPath"] = str(log_dir / "weekly-launchd.log")
    write_text_output(args.output, plistlib.dumps(config).decode("utf-8"))
    print(f"Generated {args.output}; schedule has not been loaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
