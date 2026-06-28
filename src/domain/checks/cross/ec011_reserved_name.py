from application._registry import register
from domain.checks._codes import EC011
from domain.checks._opcode_sets import builtin_opcodes, resolve_opcode
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.symbols import SymbolTable

# Reserved names are the full set across all versions — an AOI named "EQ"
# would shadow the v36+ builtin even on older projects.
_RESERVED_NAMES = builtin_opcodes("99.00")


_reported: set[str] = set()


def _reset():
    _reported.clear()


@register
def ec011_reserved_name(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    global _reported
    result: list[Diagnostic] = []
    for name in symbols.aoi_names:
        canonical = resolve_opcode(name, symbols.software_revision)
        if canonical in _RESERVED_NAMES and name not in _reported:
            _reported.add(name)
            result.append(
                Diagnostic(
                    code=EC011.code,
                    severity=EC011.severity,
                    location=loc,
                    message=EC011(name=name, kind="AOI").message,
                )
            )
    for prog_name in symbols.program_tags:
        canonical = resolve_opcode(prog_name, symbols.software_revision)
        if canonical in _RESERVED_NAMES and prog_name not in _reported:
            _reported.add(prog_name)
            result.append(
                Diagnostic(
                    code=EC011.code,
                    severity=EC011.severity,
                    location=loc,
                    message=EC011(name=prog_name, kind="Program").message,
                )
            )
    return result
