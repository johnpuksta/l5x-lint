from application._registry import register
from domain.checks._codes import WR007
from domain.checks._opcode_sets import INPUT_OPCODES, OUTPUT_OPCODES
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.symbols import SymbolTable


@register
def wr007_inputs_no_output(
    routine: Routine,
    _symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    if routine.type != "RLL" or not routine.rll_rungs:
        return result

    for rung in routine.rll_rungs:
        state = _RungState()
        _classify_rung_state(rung.instructions, state)
        if state.has_input and not state.has_output:
            result.append(
                Diagnostic(
                    code=WR007.code,
                    severity=WR007.severity,
                    location=Location(
                        program=loc.program,
                        routine=loc.routine,
                        rung=rung.number,
                    ),
                    message=WR007(rung=rung.number).message,
                )
            )

    return result


class _RungState:
    def __init__(self):
        self.has_input = False
        self.has_output = False


def _classify_rung_state(instructions, state: _RungState):
    for inst in instructions:
        opcode = inst.opcode.upper()
        if opcode in INPUT_OPCODES:
            state.has_input = True
        if opcode in OUTPUT_OPCODES:
            state.has_output = True
        if inst.branch:
            for path in inst.branch:
                _classify_rung_state(path, state)
