from returns.maybe import Some

from application.analyze import register
from domain.checks._codes import WR004
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.symbols import SymbolTable


@register
def wr004_timer_pre(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
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
                            code=WR004.code,
                            severity=WR004.severity,
                            location=Location(
                                program=loc.program, routine=loc.routine, rung=rung_num
                            ),
                            message=WR004(name=tag_name).message,
                        )
                    )

    return result
