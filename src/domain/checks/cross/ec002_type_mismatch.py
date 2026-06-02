from returns.maybe import Some

from application.analyze import register
from domain.checks._codes import EC002
from domain.checks.opcodes import INSTRUCTION_TYPES
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.symbols import SymbolTable


@register
def ec002_type_mismatch(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
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
                    match symbols.resolve(tag_name, loc.program):
                        case Some(tag) if tag.data_type.upper() != expected_type:
                            result.append(
                                Diagnostic(
                                    code=EC002.code,
                                    severity=EC002.severity,
                                    location=Location(
                                        program=loc.program,
                                        routine=loc.routine,
                                        rung=rung_num,
                                    ),
                                    message=EC002(
                                        expected=expected_type,
                                        actual=tag.data_type,
                                    ).message,
                                )
                            )
        if inst.branch:
            for path in inst.branch:
                _check_rll(path, symbols, loc, rung_num, result)


def _check_st(body, symbols, loc, result):
    from domain.st_models import StCall

    for stmt in body.statements:
        if isinstance(stmt, StCall):
            opcode = stmt.name.upper()
            expected_types = INSTRUCTION_TYPES.get(opcode)
            if expected_types and stmt.args:
                for idx, expected_type in expected_types.items():
                    if idx < len(stmt.args):
                        _check_st_arg(
                            stmt.args[idx], expected_type, symbols, loc, result
                        )


def _check_st_arg(expr, expected_type, symbols, loc, result):
    from domain.st_models import StTagRef

    if not isinstance(expr, StTagRef):
        return
    tag_name = expr.path.segments[0].name if expr.path.segments else ""
    if not tag_name:
        return
    match symbols.resolve(tag_name, loc.program):
        case Some(tag) if tag.data_type.upper() != expected_type:
            result.append(
                Diagnostic(
                    code=EC002.code,
                    severity=EC002.severity,
                    location=loc,
                    message=EC002(expected=expected_type, actual=tag.data_type).message,
                )
            )
