import re

from returns.maybe import Nothing

from application.analyze import register
from domain.checks._codes import EC001
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.st_models import (
    StAssignment,
    StBinaryOp,
    StCall,
    StCase,
    StExit,
    StFor,
    StIf,
    StJsr,
    StLiteral,
    StProgram,
    StRepeat,
    StReturn,
    StTagRef,
    StUnaryOp,
    StWhile,
)
from domain.symbols import SymbolTable

_DiagList = list[Diagnostic]

_NUMBER = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")
_BASE = re.compile(r"^([A-Za-z_][A-Za-z0-9_:]*?)(?:[.\[]|$)")
_SKIP = frozenset({"true", "false", "TRUE", "FALSE"})


def _extract_base(value: str) -> str | None:
    s = value.strip()
    if not s or s == "?" or s in _SKIP:
        return None
    if _NUMBER.match(s):
        return None
    if s.startswith(('"', "'")):
        return None
    m = _BASE.match(s)
    return m.group(1) if m else None


def _check_rll_instructions(
    instructions,
    symbols: SymbolTable,
    loc: Location,
    rung_num: int,
    result: _DiagList,
) -> None:
    for inst in instructions:
        operands = inst.operands
        if inst.opcode.upper() in ("JSR", "JXR"):
            operands = operands[1:]
        for op in operands:
            base = _extract_base(op.value)
            if base is None:
                continue
            match symbols.resolve(base, loc.program):
                case x if x is Nothing:
                    result.append(
                        Diagnostic(
                            code=EC001.code,
                            severity=EC001.severity,
                            location=Location(
                                program=loc.program, routine=loc.routine, rung=rung_num
                            ),
                            message=EC001(name=base).message,
                        )
                    )
        if inst.branch:
            for branch_path in inst.branch:
                _check_rll_instructions(branch_path, symbols, loc, rung_num, result)


def _check_rll(routine: Routine, symbols: SymbolTable, loc: Location) -> _DiagList:
    result: list[Diagnostic] = []
    for rung in routine.rll_rungs:
        _check_rll_instructions(rung.instructions, symbols, loc, rung.number, result)
    return result


def _expr_tags(expr) -> list[str]:
    match expr:
        case StTagRef():
            return [expr.path.segments[0].name] if expr.path.segments else []
        case StBinaryOp():
            return _expr_tags(expr.left) + _expr_tags(expr.right)
        case StUnaryOp():
            return _expr_tags(expr.operand)
        case StLiteral():
            return []
        case StCall():
            result = []
            for a in expr.args:
                result.extend(_expr_tags(a))
            return result
        case _:
            return []


def _stmt_tags(stmt) -> list[str]:
    match stmt:
        case StAssignment():
            result = [stmt.target.segments[0].name] if stmt.target.segments else []
            result.extend(_expr_tags(stmt.expression))
            return result
        case StIf():
            result = _expr_tags(stmt.condition)
            for s in stmt.body:
                result.extend(_stmt_tags(s))
            for _, body in stmt.elsif_pairs:
                for s in body:
                    result.extend(_stmt_tags(s))
            for s in stmt.else_body:
                result.extend(_stmt_tags(s))
            return result
        case StCase():
            result = _expr_tags(stmt.expression)
            for _, body in stmt.cases:
                for s in body:
                    result.extend(_stmt_tags(s))
            for s in stmt.else_body:
                result.extend(_stmt_tags(s))
            return result
        case StFor():
            result = [stmt.variable.segments[0].name] if stmt.variable.segments else []
            result.extend(_expr_tags(stmt.start))
            result.extend(_expr_tags(stmt.end))
            if stmt.step is not None:
                result.extend(_expr_tags(stmt.step))
            for s in stmt.body:
                result.extend(_stmt_tags(s))
            return result
        case StWhile():
            result = _expr_tags(stmt.condition)
            for s in stmt.body:
                result.extend(_stmt_tags(s))
            return result
        case StRepeat():
            result = []
            for s in stmt.body:
                result.extend(_stmt_tags(s))
            if stmt.until is not None:
                result.extend(_expr_tags(stmt.until))
            return result
        case StCall():
            return _expr_tags(stmt)
        case StJsr():
            result = []
            for a in stmt.args:
                result.extend(_expr_tags(a))
            return result
        case StExit():
            return []
        case StReturn():
            return []
        case _:
            return []


def _check_st(routine: Routine, symbols: SymbolTable, loc: Location) -> _DiagList:
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return []
    tags = []
    for stmt in bod.statements:
        tags.extend(_stmt_tags(stmt))
    result: list[Diagnostic] = []
    for name in tags:
        match symbols.resolve(name, loc.program):
            case x if x is Nothing:
                result.append(
                    Diagnostic(
                        code=EC001.code,
                        severity=EC001.severity,
                        location=loc,
                        message=EC001(name=name).message,
                    )
                )
    return result


@register
def ec001_undefined_tag(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> _DiagList:
    if routine.type == "RLL" and routine.rll_rungs:
        return _check_rll(routine, symbols, loc)
    if routine.type == "ST":
        return _check_st(routine, symbols, loc)
    return []
