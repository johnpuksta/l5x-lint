from l5x_lint.checks._codes import WS104
from l5x_lint.checks._types import expression_type
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StIf, StProgram, StRepeat, StWhile
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def ws104_non_bool_condition(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return result
    for stmt in bod.statements:
        _check_condition(stmt, loc.program, loc.routine, symbols, result)
    return result


def _check_condition(
    stmt, program: str, routine: str, symbols: SymbolTable, result: list[Diagnostic],
) -> None:
    match stmt:
        case StIf():
            t = expression_type(stmt.condition, program, symbols)
            if t is not None and t.upper() != "BOOL":
                result.append(Diagnostic(
                    code=WS104.code, severity=WS104.severity,
                    location=Location(program=program, routine=routine, line=stmt.line),
                    message=WS104(construct="IF", actual=t).message,
                ))
            for s in stmt.body:
                _check_condition(s, program, routine, symbols, result)
            for _, body in stmt.elsif_pairs:
                for s in body:
                    _check_condition(s, program, routine, symbols, result)
            for s in stmt.else_body:
                _check_condition(s, program, routine, symbols, result)
        case StWhile():
            t = expression_type(stmt.condition, program, symbols)
            if t is not None and t.upper() != "BOOL":
                result.append(Diagnostic(
                    code=WS104.code, severity=WS104.severity,
                    location=Location(program=program, routine=routine, line=stmt.line),
                    message=WS104(construct="WHILE", actual=t).message,
                ))
            for s in stmt.body:
                _check_condition(s, program, routine, symbols, result)
        case StRepeat():
            if stmt.until is not None:
                t = expression_type(stmt.until, program, symbols)
                if t is not None and t.upper() != "BOOL":
                    result.append(Diagnostic(
                        code=WS104.code, severity=WS104.severity,
                        location=Location(program=program, routine=routine, line=stmt.line),
                        message=WS104(construct="UNTIL", actual=t).message,
                    ))
            for s in stmt.body:
                _check_condition(s, program, routine, symbols, result)
        case _:
            for child in getattr(stmt, 'body', []):
                _check_condition(child, program, routine, symbols, result)
