from l5x_lint.checks._codes import WS108
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StCall, StProgram
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable

_NO_EFFECT_CALLS: frozenset[str] = frozenset({
    "ADD", "SUB", "MUL", "DIV", "MOD", "NEG", "ABS",
    "SQR", "GT", "LT", "GEQ", "LEQ", "EQU", "NEQ",
    "AND", "OR", "NOT", "XOR",
})


@register
def ws108_no_effect(
    routine: Routine, _symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return result
    for stmt in bod.statements:
        _check_no_effect(stmt, loc, result)
    return result


def _check_no_effect(stmt, loc: Location, result: list[Diagnostic]):
    match stmt:
        case StCall(name=name):
            if name.upper() in _NO_EFFECT_CALLS:
                result.append(Diagnostic(
                    code=WS108.code, severity=WS108.severity,
                    location=Location(
                        program=loc.program, routine=loc.routine,
                        line=stmt.line,
                    ),
                    message=WS108(line=stmt.line).message,
                ))
