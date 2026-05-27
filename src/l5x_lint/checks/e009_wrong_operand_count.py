from l5x_lint.checks.opcodes import OPCODE_OPERANDS
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.errors import E009
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def e009_wrong_operand_count(
    routine: Routine, _symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    if routine.type != "RLL" or not routine.rll_rungs:
        return result

    for rung in routine.rll_rungs:
        _check_rung(rung.instructions, loc, rung.number, result)

    return result


def _check_rung(instructions, loc, rung_num, result):
    for inst in instructions:
        opcode = inst.opcode.upper()
        if opcode not in OPCODE_OPERANDS:
            continue
        min_ops, max_ops = OPCODE_OPERANDS[opcode]
        actual = len(inst.operands)

        if max_ops is not None and actual > max_ops:
            result.append(
                Diagnostic(
                    code=E009.code,
                    severity=E009.severity,
                    location=Location(
                        program=loc.program, routine=loc.routine, rung=rung_num
                    ),
                    message=E009(
                        opcode=opcode, expected=max_ops, actual=actual
                    ).message,
                )
            )
        elif min_ops is not None and actual < min_ops:
            result.append(
                Diagnostic(
                    code=E009.code,
                    severity=E009.severity,
                    location=Location(
                        program=loc.program, routine=loc.routine, rung=rung_num
                    ),
                    message=E009(
                        opcode=opcode, expected=min_ops, actual=actual
                    ).message,
                )
            )

        if inst.branch:
            for path in inst.branch:
                _check_rung(path, loc, rung_num, result)
