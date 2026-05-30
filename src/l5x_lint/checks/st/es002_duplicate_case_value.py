from l5x_lint.checks._codes import ES002
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StCase, StLiteral, StProgram
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def es002_duplicate_case_value(
    routine: Routine, _symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return result
    for stmt in bod.statements:
        _check_case(stmt, loc, result)
    return result


def _check_case(stmt, loc: Location, result: list[Diagnostic]):
    match stmt:
        case StCase():
            seen: set[str] = set()
            for values, _ in stmt.cases:
                for v in values:
                    val_str = _value_str(v)
                    if val_str is not None:
                        if val_str in seen:
                            result.append(Diagnostic(
                                code=ES002.code, severity=ES002.severity,
                                location=Location(
                                    program=loc.program, routine=loc.routine,
                                    line=stmt.line,
                                ),
                                message=ES002(value=val_str, line=stmt.line).message,
                            ))
                        else:
                            seen.add(val_str)
            for _, body in stmt.cases:
                for s in body:
                    _check_case(s, loc, result)
            for s in stmt.else_body:
                _check_case(s, loc, result)


def _value_str(expr) -> str | None:
    match expr:
        case StLiteral(value=v):
            return str(v)
        case _:
            return None
