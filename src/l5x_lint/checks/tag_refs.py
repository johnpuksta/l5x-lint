import re

from l5x_lint.domain.models import Routine
from l5x_lint.domain.st_models import (
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

_NUMBER = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")
_BASE = re.compile(r"^([A-Za-z_][A-Za-z0-9_:]*?)(?:[.\[]|$)")
_SKIP = frozenset({"true", "false", "TRUE", "FALSE"})


def extract_base(value: str) -> str | None:
    s = value.strip()
    if not s or s == "?" or s in _SKIP:
        return None
    if _NUMBER.match(s):
        return None
    if s.startswith(('"', "'")):
        return None
    m = _BASE.match(s)
    return m.group(1) if m else None


def rll_tag_refs(routine: Routine) -> set[str]:
    tags: set[str] = set()
    _walk_rll_instructions(routine.rll_rungs, tags)
    return tags


def _walk_rll_instructions(rungs, tags: set[str]) -> None:
    for rung in rungs:
        _walk_rung_instructions(rung.instructions, tags)


def _walk_rung_instructions(instructions, tags: set[str]) -> None:
    for inst in instructions:
        operands = inst.operands
        if inst.opcode.upper() in ("JSR", "JXR"):
            operands = operands[1:]
        for op in operands:
            base = extract_base(op.value)
            if base is not None:
                tags.add(base)
        if inst.branch:
            for path in inst.branch:
                _walk_rung_instructions(path, tags)
        if hasattr(inst, "output_branches") and inst.output_branches:
            for path in inst.output_branches:
                _walk_rung_instructions(path, tags)


def st_tag_refs(routine: Routine) -> set[str]:
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return set()
    tags: set[str] = set()
    for stmt in bod.statements:
        _stmt_tags(stmt, tags)
    return tags


def _stmt_tags(stmt, tags: set[str]) -> None:
    match stmt:
        case StAssignment():
            if stmt.target.segments:
                tags.add(stmt.target.segments[0].name)
            _expr_tags(stmt.expression, tags)
        case StIf():
            _expr_tags(stmt.condition, tags)
            for s in stmt.body:
                _stmt_tags(s, tags)
            for _, body in stmt.elsif_pairs:
                for s in body:
                    _stmt_tags(s, tags)
            for s in stmt.else_body:
                _stmt_tags(s, tags)
        case StCase():
            _expr_tags(stmt.expression, tags)
            for _, body in stmt.cases:
                for s in body:
                    _stmt_tags(s, tags)
            for s in stmt.else_body:
                _stmt_tags(s, tags)
        case StFor():
            if stmt.variable.segments:
                tags.add(stmt.variable.segments[0].name)
            _expr_tags(stmt.start, tags)
            _expr_tags(stmt.end, tags)
            if stmt.step is not None:
                _expr_tags(stmt.step, tags)
            for s in stmt.body:
                _stmt_tags(s, tags)
        case StWhile():
            _expr_tags(stmt.condition, tags)
            for s in stmt.body:
                _stmt_tags(s, tags)
        case StRepeat():
            for s in stmt.body:
                _stmt_tags(s, tags)
            if stmt.until is not None:
                _expr_tags(stmt.until, tags)
        case StCall():
            _expr_tags(stmt, tags)
        case StJsr():
            for a in stmt.args:
                _expr_tags(a, tags)
        case StExit() | StReturn():
            pass


def _expr_tags(expr, tags: set[str]) -> None:
    match expr:
        case StTagRef():
            if expr.path.segments:
                tags.add(expr.path.segments[0].name)
        case StBinaryOp():
            _expr_tags(expr.left, tags)
            _expr_tags(expr.right, tags)
        case StUnaryOp():
            _expr_tags(expr.operand, tags)
        case StLiteral():
            pass
        case StCall():
            for a in expr.args:
                _expr_tags(a, tags)


def collect_all_tag_refs(routine: Routine) -> set[str]:
    if routine.type == "RLL" and routine.rll_rungs:
        return rll_tag_refs(routine)
    if routine.type == "ST":
        return st_tag_refs(routine)
    return set()
