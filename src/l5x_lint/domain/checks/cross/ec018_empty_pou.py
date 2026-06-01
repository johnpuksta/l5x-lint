from l5x_lint.domain.checks._codes import EC018
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.application.analyze import register
from l5x_lint.domain.symbols import SymbolTable

_processed: bool = False


def _reset():
    global _processed
    _processed = False


@register
def ec018_empty_pou(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    global _processed
    result: list[Diagnostic] = []

    if not _processed:
        _processed = True
        if not symbols.routine_names:
            result.append(
                Diagnostic(
                    code=EC018.code,
                    severity=EC018.severity,
                    location=loc,
                    message=EC018(detail="Controller has no defined routines").message,
                )
            )
            return result

    has_body = (
        (routine.type == "ST" and routine.st_body is not None)
        or (routine.type == "RLL" and routine.rll_rungs)
        or bool(routine.cdata)
    )
    if not has_body:
        result.append(
            Diagnostic(
                code=EC018.code,
                severity=EC018.severity,
                location=loc,
                message=EC018(
                    detail=f"Routine '{routine.name}' has no body content"
                ).message,
            )
        )

    return result
