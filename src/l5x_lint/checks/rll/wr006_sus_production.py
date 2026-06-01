from l5x_lint.checks._codes import WR006
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.domain.symbols import SymbolTable


@register
def wr006_sus_production(
    routine: Routine,
    _symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    if routine.type != "RLL" or not routine.rll_rungs:
        return result

    for rung in routine.rll_rungs:
        _check_sus(rung.instructions, rung.number, loc, result)

    return result


def _check_sus(instructions, rung_num: int, loc: Location, result: list[Diagnostic]):
    for inst in instructions:
        if inst.opcode.upper() == "SUS":
            result.append(
                Diagnostic(
                    code=WR006.code,
                    severity=WR006.severity,
                    location=Location(
                        program=loc.program,
                        routine=loc.routine,
                        rung=rung_num,
                    ),
                    message=WR006(rung=rung_num).message,
                )
            )
        if inst.branch:
            for path in inst.branch:
                _check_sus(path, rung_num, loc, result)
