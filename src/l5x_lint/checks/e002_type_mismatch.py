from l5x_lint.checks._codes import E002
from l5x_lint.checks.opcodes import INSTRUCTION_TYPES
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def e002_type_mismatch(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    if routine.type == "RLL":
        for rung in routine.rll_rungs:
            _check_rll(rung.instructions, symbols, loc, rung.number, result)

    if routine.type == "ST" and hasattr(routine.st_body, "statements"):
        _check_st(routine.st_body, symbols, loc, result)

    return result


def _check_rll(instructions, symbols, loc, rung_num, result):
    for inst in instructions:
        opcode = inst.opcode.upper()
        expected_types = INSTRUCTION_TYPES.get(opcode)
        if expected_types and inst.operands:
            for idx, expected_type in expected_types.items():
                if idx < len(inst.operands):
                    tag_name = inst.operands[idx].value
                    resolved = symbols.resolve(tag_name, loc.program).value_or(None)
                    if resolved is not None and resolved.data_type.upper() != expected_type:  # noqa: E501
                        result.append(
                            Diagnostic(
                                code=E002.code,
                                severity=E002.severity,
                                location=Location(
                                    program=loc.program, routine=loc.routine, rung=rung_num  # noqa: E501
                                ),
                                message=E002(expected=expected_type, actual=resolved.data_type).message,  # noqa: E501
                            )
                        )
        if inst.branch:
            for path in inst.branch:
                _check_rll(path, symbols, loc, rung_num, result)


def _check_st(body, symbols, loc, result):
    from l5x_lint.domain.st_models import StCall
    for stmt in body.statements:
        if isinstance(stmt, StCall):
            opcode = stmt.name.upper()
            expected_types = INSTRUCTION_TYPES.get(opcode)
            if expected_types and stmt.args:
                for idx, expected_type in expected_types.items():
                    if idx < len(stmt.args):
                        _check_st_arg(stmt.args[idx], expected_type, symbols, loc, result)  # noqa: E501


def _check_st_arg(expr, expected_type, symbols, loc, result):
    from l5x_lint.domain.st_models import StTagRef
    if not isinstance(expr, StTagRef):
        return
    tag_name = expr.path.segments[0].name if expr.path.segments else ""
    if not tag_name:
        return
    resolved = symbols.resolve(tag_name, loc.program).value_or(None)
    if resolved is not None and resolved.data_type.upper() != expected_type:
        result.append(
            Diagnostic(
                code=E002.code,
                severity=E002.severity,
                location=loc,
                message=E002(expected=expected_type, actual=resolved.data_type).message,
            )
        )
