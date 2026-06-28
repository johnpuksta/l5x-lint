from returns.maybe import Some

from domain.checks._opcode_sets import BIT_OPS, COMPARE_OPS, MATH_OPS
from domain.st_models import (
    StBinaryOp,
    StCall,
    StLiteral,
    StTagRef,
    StUnaryOp,
)
from domain.symbols import BUILTIN_TYPES, SymbolTable

# Math ops return None (void); bit and compare ops return BOOL.
# MOVE is a math op (returns void like MOV).
_RETURN_BOOL = BIT_OPS | COMPARE_OPS


def _call_return_type(name: str, symbols: SymbolTable) -> str | None:
    upper = name.upper()
    if upper in _RETURN_BOOL:
        return "BOOL"
    if upper in MATH_OPS:
        return None
    return None


def _tag_ref_type(segments, program: str, symbols: SymbolTable) -> str | None:
    tag = symbols.resolve(segments[0].name, program)
    match tag:
        case Some(t) if t.data_type.upper() in BUILTIN_TYPES:
            current = t.data_type.upper()
        case Some(t):
            base = symbols.resolve_type(segments[0].name, program)
            if base is None:
                return None
            current = base.name
        case _:
            return None
    for seg in segments[1:]:
        dt = symbols.resolve_member_type(current, seg.name)
        if dt is None:
            return None
        current = dt.name
    return current


def expression_type(expr, program: str, symbols: SymbolTable) -> str | None:
    match expr:
        case StTagRef() if expr.path.segments:
            return _tag_ref_type(expr.path.segments, program, symbols)
        case StLiteral(value=int()):
            return "DINT"
        case StLiteral(value=float()):
            return "REAL"
        case StLiteral(value=bool()):
            return "BOOL"
        case StBinaryOp():
            left = expression_type(expr.left, program, symbols)
            right = expression_type(expr.right, program, symbols)
            if left == "REAL" or right == "REAL":
                return "REAL"
            if left is not None and right is not None:
                return left
            return None
        case StUnaryOp():
            return expression_type(expr.operand, program, symbols)
        case StCall(name=name):
            return _call_return_type(name, symbols)
        case _:
            return None
