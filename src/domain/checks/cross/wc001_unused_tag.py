from application.analyze import register
from domain.checks._codes import WC001
from domain.checks.tag_refs import collect_all_tag_refs
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.symbols import SymbolTable

_reported: set[str] = set()


def _reset():
    _reported.clear()


@register
def wc001_unused_tag(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    used = collect_all_tag_refs(routine)
    result: list[Diagnostic] = []

    for t in symbols.controller_tags.values():
        key = f"ctrl:{t.name}"
        if key not in _reported and t.name not in used:
            _reported.add(key)
            result.append(
                Diagnostic(
                    code=WC001.code,
                    severity=WC001.severity,
                    location=loc,
                    message=WC001(name=t.name).message,
                )
            )

    for t in symbols.program_tags.get(loc.program, {}).values():
        key = f"{loc.program}:{t.name}"
        if key not in _reported and t.name not in used:
            _reported.add(key)
            result.append(
                Diagnostic(
                    code=WC001.code,
                    severity=WC001.severity,
                    location=loc,
                    message=WC001(name=t.name).message,
                )
            )

    return result
