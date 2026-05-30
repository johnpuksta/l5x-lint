from l5x_lint.checks._codes import ES001
from l5x_lint.checks._types import expression_type
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StBinaryOp, StProgram
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable

_STRING_TYPES: frozenset[str] = frozenset({"STRING"})
_NUMERIC_TYPES: frozenset[str] = frozenset({
    "SINT", "INT", "DINT", "LINT",
    "USINT", "UINT", "UDINT", "ULINT",
    "REAL", "LREAL",
})


@register
def es001_invalid_expression_op(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return result
    for stmt in bod.statements:
        _walk_ops(stmt, symbols, loc, result)
    return result


def _walk_ops(expr, symbols: SymbolTable, loc: Location, result: list[Diagnostic]):
    match expr:
        case StBinaryOp():
            left_t = expression_type(expr.left, loc.program, symbols)
            right_t = expression_type(expr.right, loc.program, symbols)
            if left_t and right_t:
                _check_binary_op(
                    left_t.upper(), expr.op.upper(), right_t.upper(),
                    loc, result,
                )
            _walk_ops(expr.left, symbols, loc, result)
            _walk_ops(expr.right, symbols, loc, result)
        case _:
            for child in getattr(expr, 'left', None), getattr(expr, 'right', None):
                if child is not None:
                    _walk_ops(child, symbols, loc, result)
            for child in getattr(expr, 'body', []):
                _walk_ops(child, symbols, loc, result)


def _check_binary_op(
    left_t: str, op: str, right_t: str,
    loc: Location, result: list[Diagnostic],
):
    if left_t in _STRING_TYPES and right_t not in _STRING_TYPES:
        result.append(Diagnostic(
            code=ES001.code, severity=ES001.severity,
            location=loc,
            message=ES001(left_type=left_t, op=op, right_type=right_t).message,
        ))
    elif right_t in _STRING_TYPES and left_t not in _STRING_TYPES:
        result.append(Diagnostic(
            code=ES001.code, severity=ES001.severity,
            location=loc,
            message=ES001(left_type=left_t, op=op, right_type=right_t).message,
        ))
