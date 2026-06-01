import re

from returns.maybe import Some

from l5x_lint.domain.checks._codes import EC006
from l5x_lint.domain.checks.tag_refs import extract_base
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.application.analyze import register
from l5x_lint.domain.symbols import SymbolTable

_ARRAY_INDEX_BRACKET = re.compile(r"^[A-Za-z_][A-Za-z0-9_:]*\[(\d+)\]")
_ARRAY_INDEX_DOT = re.compile(r"^([A-Za-z_][A-Za-z0-9_:]*)\.(\d+)(?:\.|$)")


@register
def ec006_array_bounds(
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
        for op in inst.operands:
            _check_operand(op.value, symbols, loc, result, rung_num)
        if inst.branch:
            for path in inst.branch:
                _check_rll(path, symbols, loc, rung_num, result)


def _check_operand(value, symbols, loc, result, rung_num=None):
    m = _ARRAY_INDEX_BRACKET.search(value)
    if m:
        index = int(m.group(1))
        base_name = extract_base(value)
    else:
        m = _ARRAY_INDEX_DOT.match(value)
        if not m:
            return
        base_name = m.group(1)
        index = int(m.group(2))
    if base_name is None:
        return
    match symbols.resolve(base_name, loc.program):
        case Some(tag):
            if not tag.dimensions:
                return
            size = tag.dimensions[0]
            if index >= size:
                result.append(
                    Diagnostic(
                        code=EC006.code,
                        severity=EC006.severity,
                        location=Location(
                            program=loc.program, routine=loc.routine, rung=rung_num
                        ),
                        message=EC006(name=base_name, index=index, size=size).message,
                    )
                )


def _check_st(body, symbols, loc, result):
    _check_st_exprs(body, symbols, loc, None, result)


def _check_st_exprs(node, symbols, loc, _line, result):
    from l5x_lint.domain.st_models import StAssignment, StTagRef

    if isinstance(node, StAssignment):
        if node.target.segments:
            seg = node.target.segments[0]
            if seg.index is not None:
                _check_index(
                    node.target.segments[0].name, seg.index, symbols, loc, result
                )
        _check_st_exprs(node.expression, symbols, loc, None, result)
    elif isinstance(node, StTagRef):
        if node.path.segments:
            seg = node.path.segments[0]
            if seg.index is not None:
                _check_index(seg.name, seg.index, symbols, loc, result)
    elif hasattr(node, "statements"):
        for s in node.statements:
            _check_st_exprs(s, symbols, loc, None, result)
    elif hasattr(node, "body"):
        for s in node.body:
            _check_st_exprs(s, symbols, loc, None, result)


def _check_index(
    name: str,
    index: int,
    symbols: SymbolTable,
    loc: Location,
    result: list,
) -> None:
    match symbols.resolve(name, loc.program):
        case Some(tag):
            if not tag.dimensions:
                return
            size = tag.dimensions[0]
            if index >= size:
                result.append(
                    Diagnostic(
                        code=EC006.code,
                        severity=EC006.severity,
                        location=loc,
                        message=EC006(name=name, index=index, size=size).message,
                    )
                )
