from l5x_lint.checks._codes import WS109
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import (
    StAssignment, StFor, StProgram,
)
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def ws109_for_var_assign(
    routine: Routine, _symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return result
    for stmt in bod.statements:
        _check_for_loop(stmt, loc, result)
    return result


def _check_for_loop(stmt, loc: Location, result: list[Diagnostic]):
    match stmt:
        case StFor():
            var_name = stmt.variable.segments[0].name.upper() if stmt.variable.segments else None
            if var_name:
                _walk_body_for_assign(stmt.body, var_name, loc, result)
            for s in stmt.body:
                _check_for_loop(s, loc, result)


def _walk_body_for_assign(stmts, for_var: str, loc: Location, result: list[Diagnostic]):
    for s in stmts:
        match s:
            case StAssignment():
                target_name = s.target.segments[0].name.upper() if s.target.segments else ""
                if target_name == for_var:
                    result.append(Diagnostic(
                        code=WS109.code, severity=WS109.severity,
                        location=Location(
                            program=loc.program, routine=loc.routine,
                            line=s.line,
                        ),
                        message=WS109(name=target_name.lower(), line=s.line).message,
                    ))
