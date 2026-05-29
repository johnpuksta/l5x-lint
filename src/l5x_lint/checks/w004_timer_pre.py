from returns.maybe import Some

from l5x_lint.checks._codes import W004
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def w004_timer_pre(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    if routine.type == "RLL":
        for rung in routine.rll_rungs:
            _check_rll(rung.instructions, symbols, loc, rung.number, result)

    return result


def _check_rll(instructions, symbols, loc, rung_num, result):
    for inst in instructions:
        opcode = inst.opcode.upper()
        if opcode in ("TON", "TOF", "RTO") and inst.operands:
            tag_name = inst.operands[0].value
            match symbols.resolve(tag_name, loc.program):
                case Some(tag) if tag.data_type.upper() == "TIMER":
                    result.append(
                        Diagnostic(
                            code=W004.code,
                            severity=W004.severity,
                            location=Location(
                                program=loc.program, routine=loc.routine, rung=rung_num
                            ),
                            message=W004(name=tag_name).message,
                        )
                    )
        if inst.branch:
            for path in inst.branch:
                _check_rll(path, symbols, loc, rung_num, result)
