from l5x_lint.checks._codes import W003
from l5x_lint.checks.opcodes import INPUT_OPCODES, OUTPUT_OPCODES
from l5x_lint.checks.tag_refs import extract_base
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def w003_output_never_driven(
    routine: Routine, _symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    if routine.type != "RLL" or not routine.rll_rungs:
        return []

    inputs: set[str] = set()
    outputs: set[str] = set()

    for rung in routine.rll_rungs:
        _walk_rung(rung.instructions, inputs, outputs)

    result: list[Diagnostic] = []
    for name in inputs:
        if name not in outputs:
            result.append(
                Diagnostic(
                    code=W003.code,
                    severity=W003.severity,
                    location=loc,
                    message=W003(name=name).message,
                )
            )
    return result


def _walk_rung(instructions, inputs: set[str], outputs: set[str]) -> None:
    for inst in instructions:
        opcode = inst.opcode.upper()
        op_values = [op.value for op in inst.operands]
        if opcode in ("JSR", "JXR"):
            op_values = op_values[1:]

        if opcode in INPUT_OPCODES:
            for v in op_values:
                base = extract_base(v)
                if base is not None:
                    inputs.add(base)

        if opcode in OUTPUT_OPCODES:
            for v in op_values:
                base = extract_base(v)
                if base is not None:
                    outputs.add(base)

        if inst.branch:
            for path in inst.branch:
                _walk_rung(path, inputs, outputs)

        if hasattr(inst, "output_branches") and inst.output_branches:
            for path in inst.output_branches:
                _walk_rung(path, inputs, outputs)
