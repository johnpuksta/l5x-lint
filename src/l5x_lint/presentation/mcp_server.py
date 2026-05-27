from __future__ import annotations

import json
from pathlib import Path

from returns.result import Failure, Success

import l5x_lint.checks  # noqa: F401 — registers all check functions
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.infrastructure.adapter import parse_l5x
from l5x_lint.pipeline.analyze import analyze

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as _e:
    msg = "mcp package is required. Install with: pip install l5x-lint[mcp]"
    raise ImportError(msg) from _e


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


def _validate(path: Path) -> str:
    result = parse_l5x(path)
    match result:
        case Failure(err):
            return json.dumps({"error": str(err)})
        case Success(project):
            pass

    analysis = analyze(project.controller)
    match analysis:
        case Failure(err):
            return json.dumps({"error": f"Analysis error: {err}"})
        case Success(ar):
            pass

    return json.dumps({
        "passed": ar.passed,
        "error_count": ar.error_count,
        "warning_count": ar.warning_count,
        "diagnostics": [_diagnostic_to_dict(d) for d in ar.diagnostics],
    }, indent=2)


def create_server() -> FastMCP:
    server = FastMCP(
        "l5x-lint",
        instructions="Lint and analyze Rockwell L5X PLC program files.",
    )

    @server.tool(
        name="validate_l5x",
        description="Validate an L5X PLC program file and return diagnostics as JSON.",
    )
    def validate_l5x(file_path: str) -> str:
        return _validate(Path(file_path))

    return server


def main() -> None:
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
