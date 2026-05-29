import re

from l5x_lint.checks._codes import E005
from l5x_lint.checks.tag_refs import extract_base
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable

_MEMBER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.([A-Za-z_][A-Za-z0-9_]*)")


@register
def e005_invalid_member(
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
        for op in inst.operands:
            _check_operand(op.value, symbols, loc, result, rung_num)
        if inst.branch:
            for path in inst.branch:
                _check_rll(path, symbols, loc, rung_num, result)


def _check_operand(value, symbols, loc, result, rung_num=None):
    m = _MEMBER_RE.match(value)
    if not m:
        return
    base_name = extract_base(value)
    if base_name is None:
        return
    member_name = m.group(1)
    resolved = symbols.resolve(base_name, loc.program).value_or(None)
    if resolved is None:
        return
    dt = symbols.data_types.get(resolved.data_type)
    if dt is None:
        return
    if not any(mem.name == member_name for mem in dt.members):
        result.append(
            Diagnostic(
                code=E005.code,
                severity=E005.severity,
                location=Location(
                    program=loc.program, routine=loc.routine, rung=rung_num
                ),
                message=E005(path=base_name, member=member_name).message,
            )
        )


def _check_st(body, symbols, loc, result):
    from l5x_lint.domain.st_models import StAssignment
    for stmt in body.statements:
        if isinstance(stmt, StAssignment):
            target = stmt.target
            if len(target.segments) >= 2:
                base_name = target.segments[0].name
                member_name = target.segments[1].name
                _check_member(base_name, member_name, symbols, loc, result)
            _check_expr_members(stmt.expression, symbols, loc, result)


def _check_expr_members(expr, symbols, loc, result):
    from l5x_lint.domain.st_models import StBinaryOp, StCall, StTagRef, StUnaryOp
    match expr:
        case StTagRef():
            if len(expr.path.segments) >= 2:
                base_name = expr.path.segments[0].name
                member_name = expr.path.segments[1].name
                _check_member(base_name, member_name, symbols, loc, result)
        case StBinaryOp():
            _check_expr_members(expr.left, symbols, loc, result)
            _check_expr_members(expr.right, symbols, loc, result)
        case StUnaryOp():
            _check_expr_members(expr.operand, symbols, loc, result)
        case StCall():
            for a in expr.args:
                _check_expr_members(a, symbols, loc, result)


def _check_member(base_name, member_name, symbols, loc, result):
    resolved = symbols.resolve(base_name, loc.program).value_or(None)
    if resolved is None:
        return
    dt = symbols.data_types.get(resolved.data_type)
    if dt is None:
        return
    if not any(mem.name == member_name for mem in dt.members):
        result.append(
            Diagnostic(
                code=E005.code,
                severity=E005.severity,
                location=loc,
                message=E005(path=base_name, member=member_name).message,
            )
        )
