from l5x_lint.checks._codes import WS113
from l5x_lint.checks._types import expression_type
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StBinaryOp, StProgram
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable

_SHORT_CIRCUIT_OPS: frozenset[str] = frozenset({"AND_THEN", "OR_ELSE"})


@register
def ws113_and_then_or_else(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return result
    for stmt in bod.statements:
        _walk_expr(stmt, symbols, loc.program, loc.routine, result)
    return result


def _walk_expr(expr, symbols: SymbolTable, program: str, routine: str, result: list[Diagnostic]):
    match expr:
        case StBinaryOp(op=op) if op.upper() in _SHORT_CIRCUIT_OPS:
            left_t = expression_type(expr.left, program, symbols)
            right_t = expression_type(expr.right, program, symbols)
            for t, side in [(left_t, "left"), (right_t, "right")]:
                if t is not None and t.upper() != "BOOL":
                    result.append(Diagnostic(
                        code=WS113.code, severity=WS113.severity,
                        location=Location(program=program, routine=routine),
                        message=WS113(op=op.upper(), actual=t).message,
                    ))
            _walk_expr(expr.left, symbols, program, routine, result)
            _walk_expr(expr.right, symbols, program, routine, result)
        case _:
            for child in getattr(expr, 'left', None), getattr(expr, 'right', None):
                if child is not None:
                    _walk_expr(child, symbols, program, routine, result)
            for child in getattr(expr, 'body', []):
                _walk_expr(child, symbols, program, routine, result)
