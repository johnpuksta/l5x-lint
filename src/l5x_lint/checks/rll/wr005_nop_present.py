from l5x_lint.checks._codes import WR005
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def wr005_nop_present(
    routine: Routine, _symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    if routine.type != "RLL" or not routine.rll_rungs:
        return result

    for rung in routine.rll_rungs:
        _check_nop(rung.instructions, rung.number, loc, result)

    return result


def _check_nop(instructions, rung_num: int, loc: Location, result: list[Diagnostic]):
    for inst in instructions:
        if inst.opcode.upper() == "NOP":
            result.append(Diagnostic(
                code=WR005.code, severity=WR005.severity,
                location=Location(
                    program=loc.program, routine=loc.routine, rung=rung_num,
                ),
                message=WR005(rung=rung_num).message,
            ))
        if inst.branch:
            for path in inst.branch:
                _check_nop(path, rung_num, loc, result)
