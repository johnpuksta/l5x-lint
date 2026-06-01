from domain.checks._codes import EC014
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from application.analyze import register
from domain.symbols import SymbolTable

_processed: bool = False


def _reset():
    global _processed
    _processed = False


@register
def ec014_unresolved_constant(
    _routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    global _processed
    result: list[Diagnostic] = []
    if _processed:
        return result
    _processed = True

    for name, tag in symbols.controller_tags.items():
        if tag.constant and not tag.has_initial_value:
            result.append(
                Diagnostic(
                    code=EC014.code,
                    severity=EC014.severity,
                    location=loc,
                    message=EC014(name=name).message,
                )
            )

    for prog_name, tags in symbols.program_tags.items():
        prog_loc = Location(program=prog_name, routine=loc.routine)
        for name, tag in tags.items():
            if tag.constant and not tag.has_initial_value:
                result.append(
                    Diagnostic(
                        code=EC014.code,
                        severity=EC014.severity,
                        location=prog_loc,
                        message=EC014(name=name).message,
                    )
                )

    return result
