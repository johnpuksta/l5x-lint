import argparse
import json
import re
import sys
from pathlib import Path

from returns.result import Failure, Success

import l5x_lint.checks  # noqa: F401 — registers all check functions
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Controller, Location
from l5x_lint.infrastructure.adapter import parse_l5x
from l5x_lint.pipeline.analyze import analyze
from l5x_lint.pipeline.config import LintConfig, apply_severity_overrides, apply_warning_toggles


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


def _build_config(args: argparse.Namespace) -> LintConfig | None:
    if not any([args.rule_pack, args.enable_warning, args.disable_warning, args.severity_override, args.dialect != "rockwell"]):
        return None
    config = LintConfig(rule_pack=args.rule_pack or "none", dialect=args.dialect)
    config.apply_rule_pack()
    apply_warning_toggles(config, disable=args.disable_warning, enable=args.enable_warning)
    apply_severity_overrides(config, args.severity_override)
    return config


def _find_xml_line(source_lines: list[str], loc: Location) -> int | None:
    """Find the XML source line number for a diagnostic location.

    Searches for the XML element matching the program/routine/rung/line
    from the diagnostic's Location.
    """
    if not source_lines:
        return None

    # Build a search pattern based on what we know
    if loc.routine:
        # Look for <Routine Name="..." ...> or <Program Name="..." ...>
        # depending on whether we have a rung/line
        if loc.rung is not None:
            # RLL rung — look for <Rung Number="N"
            pattern = re.compile(
                rf'<Routine\s+[^>]*Name\s*=\s*"{re.escape(loc.routine)}"',
                re.IGNORECASE,
            )
            for i, line in enumerate(source_lines):
                if pattern.search(line):
                    # Now find the rung inside this routine
                    rung_pattern = re.compile(
                        rf'<Rung\s+[^>]*Number\s*=\s*"{loc.rung}"',
                        re.IGNORECASE,
                    )
                    for j in range(i + 1, min(i + 500, len(source_lines))):
                        if rung_pattern.search(source_lines[j]):
                            return j + 1
                    return i + 1
        elif loc.line is not None:
            # ST line — look for <Line Number="N"
            pattern = re.compile(
                rf'<Routine\s+[^>]*Name\s*=\s*"{re.escape(loc.routine)}"',
                re.IGNORECASE,
            )
            for i, line in enumerate(source_lines):
                if pattern.search(line):
                    line_pattern = re.compile(
                        rf'<Line\s+[^>]*Number\s*=\s*"{loc.line}"',
                        re.IGNORECASE,
                    )
                    for j in range(i + 1, min(i + 500, len(source_lines))):
                        if line_pattern.search(source_lines[j]):
                            return j + 1
                    return i + 1
        else:
            # Just routine — find the Routine element
            pattern = re.compile(
                rf'<Routine\s+[^>]*Name\s*=\s*"{re.escape(loc.routine)}"',
                re.IGNORECASE,
            )
            for i, line in enumerate(source_lines):
                if pattern.search(line):
                    return i + 1
    elif loc.program:
        # Program-level — find the Program element
        pattern = re.compile(
            rf'<Program\s+[^>]*Name\s*=\s*"{re.escape(loc.program)}"',
            re.IGNORECASE,
        )
        for i, line in enumerate(source_lines):
            if pattern.search(line):
                return i + 1

    return None


def validate(path: Path, json_output: bool = False, config: LintConfig | None = None) -> int:
    result = parse_l5x(path)
    match result:
        case Failure(err):
            print(f"Error: {err}", file=sys.stderr)
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
                xml_line = _find_xml_line(source_lines, loc)
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
    val.add_argument("--rule-pack", choices=["none", "safety", "rockwell", "iec-61131-3"],
                     default="none", help="Apply diagnostic rule pack preset")
    val.add_argument("--dialect", choices=["rockwell", "iec-61131-3", "codesys"],
                     default="rockwell", help="Select PLC dialect for check behavior")
    val.add_argument("--enable-warning", action="append", choices=["numeric", "complexity"],
                     help="Enable a warning category that is off by default")
    val.add_argument("--disable-warning", action="append",
                     choices=["unused", "unreachable", "output", "timer", "shadowed",
                              "numeric", "complexity", "conversion", "missing-else"],
                     help="Disable a warning category")
    val.add_argument("--severity-override", action="append",
                     help="Override severity: code=severity (e.g. WS101=error, WR004=off)")

    args = parser.parse_args()
    if args.command == "validate":
        config = _build_config(args)
        sys.exit(validate(args.file, json_output=args.json, config=config))
    parser.print_help()
    sys.exit(1)
