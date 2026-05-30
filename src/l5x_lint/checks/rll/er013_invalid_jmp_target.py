from l5x_lint.checks._codes import ER013
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def er013_invalid_jmp_target(
    routine: Routine, _symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    if routine.type != "RLL" or not routine.rll_rungs:
        return result

    labels: dict[str, str] = {}
    jumps: list[tuple[str, str, int]] = []

    for rung in routine.rll_rungs:
        _collect_jmp_info(rung.instructions, labels, jumps, rung.number)

    for orig_label, upper_label, rung_num in jumps:
        if upper_label not in labels:
            result.append(Diagnostic(
                code=ER013.code, severity=ER013.severity,
                location=Location(
                    program=loc.program, routine=loc.routine, rung=rung_num,
                ),
                message=ER013(label=orig_label).message,
            ))

    return result


def _collect_jmp_info(instructions, labels: dict[str, str], jumps: list[tuple[str, str, int]], rung_num: int):
    for inst in instructions:
        opcode = inst.opcode.upper()
        if opcode == "LBL" and inst.operands:
            val = inst.operands[0].value
            labels[val.upper()] = val
        elif opcode == "JMP" and inst.operands:
            val = inst.operands[0].value
            jumps.append((val, val.upper(), rung_num))
        if inst.branch:
            for path in inst.branch:
                _collect_jmp_info(path, labels, jumps, rung_num)
