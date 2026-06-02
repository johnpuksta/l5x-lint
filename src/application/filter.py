from __future__ import annotations

from application.config import LintConfig
from domain.diagnostics import Diagnostic


def filter_diagnostics(
    diagnostics: list[Diagnostic],
    config: LintConfig,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    for d in diagnostics:
        if not config.diagnostic_allowed(d.code):
            continue
        resolved = config.resolve_severity(d.code, d.severity)
        if resolved == "off":
            continue
        if resolved != d.severity:
            result.append(
                Diagnostic(
                    code=d.code,
                    severity=resolved,
                    location=d.location,
                    message=d.message,
                    hint=d.hint,
                    fix_suggestion=d.fix_suggestion,
                )
            )
        else:
            result.append(d)
    return result
