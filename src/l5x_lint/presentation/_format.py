"""Shared formatting helpers for CLI and MCP presentation layers."""
from __future__ import annotations

import re

from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location


def diagnostic_to_dict(d: Diagnostic) -> dict:
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
        "related": getattr(d, "related", None),
        "iec_reference": getattr(d, "iec_reference", None),
    }


def find_xml_line(source_lines: list[str], loc: Location) -> int | None:
    """Find the XML source line number for a diagnostic location.

    Searches for the XML element matching the program/routine/rung/line
    from the diagnostic's Location. For RLL rungs, returns the <Text>
    line (where the code is), not the <Rung> line.
    """
    if not source_lines:
        return None

    if loc.routine:
        if loc.rung is not None:
            # RLL rung — find <Rung Number="N"> then the <Text> inside it
            pattern = re.compile(
                rf'<Routine\s+[^>]*Name\s*=\s*"{re.escape(loc.routine)}"',
                re.IGNORECASE,
            )
            for i, line in enumerate(source_lines):
                if pattern.search(line):
                    rung_pattern = re.compile(
                        rf'<Rung\s+[^>]*Number\s*=\s*"{loc.rung}"',
                        re.IGNORECASE,
                    )
                    for j in range(i + 1, min(i + 500, len(source_lines))):
                        if rung_pattern.search(source_lines[j]):
                            # Found the <Rung>, now find <Text> inside it
                            for k in range(j + 1, min(j + 10, len(source_lines))):
                                if re.search(r'<Text>', source_lines[k], re.IGNORECASE):
                                    return k + 1
                            return j + 1
                    return i + 1
        elif loc.line is not None:
            # ST line — find <Line Number="N">
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
            pattern = re.compile(
                rf'<Routine\s+[^>]*Name\s*=\s*"{re.escape(loc.routine)}"',
                re.IGNORECASE,
            )
            for i, line in enumerate(source_lines):
                if pattern.search(line):
                    return i + 1
    elif loc.program:
        pattern = re.compile(
            rf'<Program\s+[^>]*Name\s*=\s*"{re.escape(loc.program)}"',
            re.IGNORECASE,
        )
        for i, line in enumerate(source_lines):
            if pattern.search(line):
                return i + 1

    return None
