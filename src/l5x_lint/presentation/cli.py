import argparse
import json
import sys
from pathlib import Path

from returns.result import Failure, Success

import l5x_lint.checks  # noqa: F401 — registers all check functions
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.infrastructure.adapter import parse_l5x
from l5x_lint.pipeline.analyze import analyze


def _diagnostic_to_dict(d: Diagnostic) -> dict:
    return {
        "code": d.code,
        "severity": d.severity,
        "location": {
            "program": d.location.program,
            "routine": d.location.routine,
            "rung": d.location.rung,
            "line": d.location.line,
        },
        "message": d.message,
        "hint": d.hint,
        "fix_suggestion": d.fix_suggestion,
    }


def validate(path: Path, json_output: bool = False) -> int:
    result = parse_l5x(path)
    match result:
        case Failure(err):
            print(f"Error: {err}", file=sys.stderr)
            return 1
        case Success(project):
            pass

    analysis = analyze(project.controller)
    match analysis:
        case Failure(err):
            print(f"Analysis error: {err}", file=sys.stderr)
            return 1
        case Success(ar):
            pass

    if json_output:
        data = {
            "passed": ar.passed,
            "error_count": ar.error_count,
            "warning_count": ar.warning_count,
            "diagnostics": [_diagnostic_to_dict(d) for d in ar.diagnostics],
        }
        print(json.dumps(data, indent=2))
    else:
        if not ar.diagnostics:
            print("No issues found.")
        else:
            for d in ar.diagnostics:
                loc = d.location
                ctx = f"{loc.program}/{loc.routine}"
                if loc.rung is not None:
                    ctx += f":{loc.rung}"
                elif loc.line is not None:
                    ctx += f":{loc.line}"
                print(f"  {d.severity.upper():7s} {d.code:5s} {ctx:40s} {d.message}")
            print(f"\n{ar.error_count} errors, {ar.warning_count} warnings")
    if not ar.passed:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="l5x-lint",
        description="Semantic analyzer / linter for Rockwell L5X PLC programs",
    )
    sub = parser.add_subparsers(dest="command")

    val = sub.add_parser("validate", help="Validate an L5X file")
    val.add_argument("file", type=Path, help="Path to .L5X file")
    val.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()
    if args.command == "validate":
        sys.exit(validate(args.file, json_output=args.json))
    parser.print_help()
    sys.exit(1)
