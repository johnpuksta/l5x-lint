from l5x_lint.checks._codes import W001
from l5x_lint.checks.tag_refs import collect_all_tag_refs
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable

_reported: set[str] = set()


def _reset():
    _reported.clear()


@register
def w001_unused_tag(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    used = collect_all_tag_refs(routine)
    result: list[Diagnostic] = []

    for t in symbols.controller_tags.values():
        key = f"ctrl:{t.name}"
        if key not in _reported and t.name not in used:
            _reported.add(key)
            result.append(
                Diagnostic(
                    code=W001.code,
                    severity=W001.severity,
                    location=loc,
                    message=W001(name=t.name).message,
                )
            )

    for t in symbols.program_tags.get(loc.program, {}).values():
        key = f"{loc.program}:{t.name}"
        if key not in _reported and t.name not in used:
            _reported.add(key)
            result.append(
                Diagnostic(
                    code=W001.code,
                    severity=W001.severity,
                    location=loc,
                    message=W001(name=t.name).message,
                )
            )

    return result
