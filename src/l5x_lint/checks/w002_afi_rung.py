from l5x_lint.checks._codes import W002
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable

_DiagList = list[Diagnostic]


@register
def w002_afi_rung(routine: Routine, _symbols: SymbolTable, loc: Location) -> _DiagList:
    if routine.type != "RLL" or not routine.rll_rungs:
        return []
    result: list[Diagnostic] = []
    for rung in routine.rll_rungs:
        if rung.instructions and rung.instructions[0].opcode == "AFI":
            result.append(
                Diagnostic(
                    code=W002.code,
                    severity=W002.severity,
                    location=Location(
                            program=loc.program, routine=loc.routine, rung=rung.number
                        ),
                    message=W002(rung=rung.number).message,
                )
            )
    return result
