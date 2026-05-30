from l5x_lint.checks._codes import WS107
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StCase, StIf, StProgram
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


def _check_stmt(stmt, loc: Location, result: list[Diagnostic]) -> None:
    match stmt:
        case StIf() if not stmt.else_body:
            result.append(Diagnostic(
                code=WS107.code, severity=WS107.severity,
                location=loc,
                message=WS107(construct="IF").message,
            ))
            for s in stmt.body:
                _check_stmt(s, loc, result)
            for _, body in stmt.elsif_pairs:
                for s in body:
                    _check_stmt(s, loc, result)
        case StIf():
            for s in stmt.body:
                _check_stmt(s, loc, result)
            for _, body in stmt.elsif_pairs:
                for s in body:
                    _check_stmt(s, loc, result)
            for s in stmt.else_body:
                _check_stmt(s, loc, result)
        case StCase() if not stmt.else_body:
            result.append(Diagnostic(
                code=WS107.code, severity=WS107.severity,
                location=loc,
                message=WS107(construct="CASE").message,
            ))
            for _, body in stmt.cases:
                for s in body:
                    _check_stmt(s, loc, result)
        case StCase():
            for _, body in stmt.cases:
                for s in body:
                    _check_stmt(s, loc, result)
            for s in stmt.else_body:
                _check_stmt(s, loc, result)
        case _:
            for child in getattr(stmt, 'body', []):
                _check_stmt(child, loc, result)


@register
def ws107_missing_else(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return result
    for stmt in bod.statements:
        _check_stmt(stmt, loc, result)
    return result
