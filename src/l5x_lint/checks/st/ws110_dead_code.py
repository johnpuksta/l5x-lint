from l5x_lint.checks._codes import WS110
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StExit, StProgram, StReturn
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def ws110_dead_code(
    routine: Routine, _symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return result
    _check_dead_code(bod.statements, result, loc)
    return result


def _check_dead_code(stmts, result: list[Diagnostic], loc: Location):
    for i, stmt in enumerate(stmts):
        match stmt:
            case StReturn():
                for dead in stmts[i + 1:]:
                    result.append(Diagnostic(
                        code=WS110.code, severity=WS110.severity,
                        location=Location(
                            program=loc.program, routine=loc.routine,
                            line=getattr(dead, 'line', 0),
                        ),
                        message=WS110(construct="RETURN", line=stmt.line).message,
                    ))
                return
            case StExit():
                for dead in stmts[i + 1:]:
                    result.append(Diagnostic(
                        code=WS110.code, severity=WS110.severity,
                        location=Location(
                            program=loc.program, routine=loc.routine,
                            line=getattr(dead, 'line', 0),
                        ),
                        message=WS110(construct="EXIT", line=stmt.line).message,
                    ))
                return
