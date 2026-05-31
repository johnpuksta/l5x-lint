from returns.maybe import Some

from l5x_lint.domain.st_models import (
    StBinaryOp,
    StCall,
    StLiteral,
    StTagRef,
    StUnaryOp,
)
from l5x_lint.pipeline.symbols import BUILTIN_TYPES, SymbolTable

_REAL_OPS: frozenset[str] = frozenset({"ADD", "SUB", "MUL", "DIV", "NEG", "MOV", "CPT"})
_BOOL_OPS: frozenset[str] = frozenset({"XIC", "XIO", "OTE", "OTL", "OTU"})
_COMPARE_OPS: frozenset[str] = frozenset({"EQU", "NEQ", "LES", "LEQ", "GRT", "GEQ", "CMP", "LIM", "GT"})


def _call_return_type(name: str, symbols: SymbolTable) -> str | None:
    upper = name.upper()
    if upper in _BOOL_OPS or upper in _COMPARE_OPS:
        return "BOOL"
    if upper in _REAL_OPS:
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
