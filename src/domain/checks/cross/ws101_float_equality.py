import re

from application._registry import register
from domain.checks._codes import WS101
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.st_models import StBinaryOp, StLiteral, StProgram
from domain.symbols import SymbolTable


def _has_float_literal(s: str) -> bool:
    return bool(re.search(r"\b\d+\.\d*[eE]?[+-]?\d*\b", s))


def _check_expr(expr, text: str, result: list[Diagnostic], loc: Location) -> None:
    match expr:
        case StBinaryOp() if expr.op in ("=", "<>"):
            left_float = False
            right_float = False
            match expr.left:
                case StLiteral(value=float()):
                    left_float = True
                case StLiteral(value=int()):
                    left_float = False
                case _:
                    left_float = _has_float_literal(str(expr.left))
            match expr.right:
                case StLiteral(value=float()):
                    right_float = True
                case StLiteral(value=int()):
                    right_float = False
                case _:
                    right_float = _has_float_literal(str(expr.right))
            if left_float or right_float:
                result.append(
                    Diagnostic(
                        code=WS101.code,
                        severity=WS101.severity,
                        location=loc,
                        message=WS101(text=text).message,
                    )
                )
        case StBinaryOp():
            _check_expr(expr.left, text, result, loc)
            _check_expr(expr.right, text, result, loc)
        case _:
            for child in getattr(expr, "args", []):
                _check_expr(child, text, result, loc)


def _check_stmt(stmt, result: list[Diagnostic], loc: Location) -> None:
    for field_name in ("condition", "expression", "start", "end", "step", "until"):
        child = getattr(stmt, field_name, None)
        if child is not None:
            _check_expr(child, str(child), result, loc)
    for body_field in ("body", "else_body"):
        children = getattr(stmt, body_field, [])
        for s in children:
            _check_stmt(s, result, loc)
    for _, body in getattr(stmt, "elsif_pairs", []):
        for s in body:
            _check_stmt(s, result, loc)
    for _, body in getattr(stmt, "cases", []):
        for s in body:
            _check_stmt(s, result, loc)


@register
def ws101_float_equality(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    if routine.type == "ST":
        bod = routine.st_body
        if isinstance(bod, StProgram):
            for stmt in bod.statements:
                _check_stmt(stmt, result, loc)
    if routine.type == "RLL":
        for rung in routine.rll_rungs:
            for inst in rung.instructions:
                for op in inst.operands:
                    if _has_float_literal(op.value):
                        for cmp_op in (
                            "EQU",
                            "NEQ",
                            "GRT",
                            "LES",
                            "GEQ",
                            "LEQ",
                            "CMP",
                            "GT",
                        ):
                            if inst.opcode.upper() == cmp_op:
                                result.append(
                                    Diagnostic(
                                        code=WS101.code,
                                        severity=WS101.severity,
                                        location=Location(
                                            program=loc.program,
                                            routine=loc.routine,
                                            rung=rung.number,
                                        ),
                                        message=WS101(
                                            text=f"{inst.opcode}({op.value})"
                                        ).message,
                                    )
                                )
    return result
