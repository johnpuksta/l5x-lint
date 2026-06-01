from domain.checks._codes import EC013
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from application.analyze import register
from domain.symbols import SymbolTable

_label_counts: dict[str, int] = {}
_reported: set[str] = set()


def _reset():
    _label_counts.clear()
    _reported.clear()


@register
def ec013_duplicate_jmp_label(
    routine: Routine,
    _symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    global _label_counts, _reported
    result: list[Diagnostic] = []
    if routine.type != "RLL" or not routine.rll_rungs:
        return result

    for rung in routine.rll_rungs:
        _count_labels(rung.instructions, _label_counts)

    for label, count in list(_label_counts.items()):
        if count > 1 and label not in _reported:
            _reported.add(label)
            result.append(
                Diagnostic(
                    code=EC013.code,
                    severity=EC013.severity,
                    location=loc,
                    message=EC013(label=label).message,
                )
            )

    return result


def _count_labels(instructions, counts: dict[str, int]):
    for inst in instructions:
        opcode = inst.opcode.upper()
        if opcode == "LBL" and inst.operands:
            label = inst.operands[0].value.upper()
            counts[label] = counts.get(label, 0) + 1
        if inst.branch:
            for path in inst.branch:
                _count_labels(path, counts)
