from __future__ import annotations

import json
from pathlib import Path

from returns.result import Failure, Success

import l5x_lint.domain.checks  # noqa: F401 — registers all check functions
from l5x_lint.infrastructure.adapter import parse_l5x
from l5x_lint.application.analyze import analyze
from l5x_lint.application.config import (
    LintConfig,
    apply_severity_overrides,
    apply_warning_toggles,
)
from l5x_lint.presentation._format import diagnostic_to_dict, find_xml_line

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as _e:
    msg = "mcp package is required. Install with: pip install l5x-lint[mcp]"
    raise ImportError(msg) from _e


def _validate(path: Path, config: LintConfig | None = None) -> str:
    result = parse_l5x(path)
    match result:
        case Failure(err):
            entry = {"error": str(err)}
            if hasattr(err, "line") and err.line is not None:
                entry["line"] = err.line
            return json.dumps(entry)
        case Success(project):
            pass

    source_lines = project.controller.source_lines

    analysis = analyze(project.controller, config=config)
    match analysis:
        case Failure(err):
            return json.dumps({"error": f"Analysis error: {err}"})
        case Success(ar):
            pass

    diagnostics = []
    for d in ar.diagnostics:
        entry = diagnostic_to_dict(d)
        xml_line = find_xml_line(source_lines, d.location)
        if xml_line is not None:
            entry["xml_line"] = xml_line
        diagnostics.append(entry)

    return json.dumps(
        {
            "passed": ar.passed,
            "error_count": ar.error_count,
            "warning_count": ar.warning_count,
            "diagnostics": diagnostics,
        },
        indent=2,
    )


def _split(s: str | None) -> list[str] | None:
    return s.split(",") if s else None


def create_server() -> FastMCP:
    server = FastMCP(
        "l5x-lint",
        instructions="Lint and analyze Rockwell L5X PLC program files.",
    )

    @server.tool(
        name="validate_l5x",
        description="Validate an L5X PLC program file and return diagnostics as JSON.",
    )
    def validate_l5x(
        file_path: str,
        rule_pack: str = "none",
        dialect: str = "rockwell",
        enable_warnings: str | None = None,
        disable_warnings: str | None = None,
        severity_overrides: str | None = None,
    ) -> str:
        config = LintConfig(rule_pack=rule_pack, dialect=dialect)
        config.apply_rule_pack()
        apply_warning_toggles(
            config, disable=_split(disable_warnings), enable=_split(enable_warnings)
        )
        apply_severity_overrides(config, _split(severity_overrides))
        return _validate(Path(file_path), config=config)

    @server.tool(
        name="validate_l5x_default",
        description="Validate an L5X file with default settings (all checks enabled).",
    )
    def validate_l5x_default(file_path: str) -> str:
        return _validate(Path(file_path))

    return server


def main() -> None:
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
