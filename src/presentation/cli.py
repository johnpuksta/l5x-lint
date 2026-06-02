import argparse
import json
import sys
from pathlib import Path

from returns.result import Failure, Success

import domain.checks  # noqa: F401 — registers all check functions
from application.analyze import analyze
from application.config import (
    LintConfig,
    apply_severity_overrides,
    apply_warning_toggles,
)
from infrastructure.adapter import parse_l5x
from presentation._format import diagnostic_to_dict, find_xml_line


def _build_config(args: argparse.Namespace) -> LintConfig | None:
    if not any(
        [
            args.rule_pack,
            args.enable_warning,
            args.disable_warning,
            args.severity_override,
            args.dialect != "rockwell",
        ]
    ):
        return None
    config = LintConfig(rule_pack=args.rule_pack or "none", dialect=args.dialect)
    config.apply_rule_pack()
    apply_warning_toggles(
        config, disable=args.disable_warning, enable=args.enable_warning
    )
    apply_severity_overrides(config, args.severity_override)
    return config


def validate(
    path: Path, json_output: bool = False, config: LintConfig | None = None
) -> int:
    result = parse_l5x(path)
    match result:
        case Failure(err):
            loc = ""
            if hasattr(err, "line") and err.line is not None:
                loc = f" at line {err.line}"
            print(f"Error{loc}: {err}", file=sys.stderr)
            return 1
        case Success(project):
            pass

    source_lines = project.controller.source_lines

    analysis = analyze(project.controller, config=config)
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
            "diagnostics": [diagnostic_to_dict(d) for d in ar.diagnostics],
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
                xml_line = find_xml_line(source_lines, loc)
                if xml_line is not None:
                    ctx += f" (line {xml_line})"
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
    val.add_argument(
        "--rule-pack",
        choices=["none", "safety", "rockwell", "iec-61131-3"],
        default="none",
        help="Apply diagnostic rule pack preset",
    )
    val.add_argument(
        "--dialect",
        choices=["rockwell", "iec-61131-3", "codesys"],
        default="rockwell",
        help="Select PLC dialect for check behavior",
    )
    val.add_argument(
        "--enable-warning",
        action="append",
        choices=["numeric", "complexity"],
        help="Enable a warning category that is off by default",
    )
    val.add_argument(
        "--disable-warning",
        action="append",
        choices=[
            "unused",
            "unreachable",
            "output",
            "timer",
            "shadowed",
            "numeric",
            "complexity",
            "conversion",
            "missing-else",
        ],
        help="Disable a warning category",
    )
    val.add_argument(
        "--severity-override",
        action="append",
        help="Override severity: code=severity (e.g. WS101=error, WR004=off)",
    )

    args = parser.parse_args()
    if args.command == "validate":
        config = _build_config(args)
        sys.exit(validate(args.file, json_output=args.json, config=config))
    parser.print_help()
    sys.exit(1)
