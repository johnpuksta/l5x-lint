from application._registry import register
from domain.checks._codes import ER014
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.symbols import SymbolTable


@register
def er014_otl_without_otu(
    routine: Routine,
    _symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    if routine.type != "RLL" or not routine.rll_rungs:
        return result

    otl_tags: set[str] = set()
    otu_tags: set[str] = set()

    for rung in routine.rll_rungs:
        _collect_latch_ops(rung.instructions, otl_tags, otu_tags)

    for tag in sorted(otl_tags - otu_tags):
        result.append(
            Diagnostic(
                code=ER014.code,
                severity=ER014.severity,
                location=Location(program=loc.program, routine=loc.routine),
                message=ER014(name=tag).message,
            )
        )

    return result


def _collect_latch_ops(instructions, otl_tags: set[str], otu_tags: set[str]):
    for inst in instructions:
        opcode = inst.opcode.upper()
        if inst.operands:
            tag = inst.operands[0].value
            if opcode == "OTL":
                otl_tags.add(tag)
            elif opcode == "OTU":
                otu_tags.add(tag)
        if inst.branch:
            for path in inst.branch:
                _collect_latch_ops(path, otl_tags, otu_tags)
