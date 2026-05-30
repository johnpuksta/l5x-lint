from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StAssignment, StProgram, StTagRef
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable

from l5x_lint.checks._codes import WS105

_NARROW_TO_WIDE: dict[str, int] = {
    "SINT": 1, "INT": 2, "DINT": 4, "LINT": 8,
    "USINT": 1, "UINT": 2, "UDINT": 4, "ULINT": 8,
    "BOOL": 0,
    "REAL": 4, "LREAL": 8,
}


def _is_downcast(from_type: str, to_type: str) -> bool:
    fw = _NARROW_TO_WIDE.get(from_type.upper())
    tw = _NARROW_TO_WIDE.get(to_type.upper())
    if fw is None or tw is None:
        return False
    return fw > tw


@register
def ws105_implicit_downcast(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    if routine.type != "ST":
        return result
    bod = routine.st_body
    if not isinstance(bod, StProgram):
        return result
    for stmt in bod.statements:
        match stmt:
            case StAssignment():
                if not stmt.target.segments:
                    continue
                target_name = stmt.target.segments[0].name
                target_type = symbols.resolve_type(target_name, loc.program)
                if target_type is None:
                    continue
                match stmt.expression:
                    case StTagRef() if stmt.expression.path.segments:
                        src_name = stmt.expression.path.segments[0].name
                        src_type = symbols.resolve_type(src_name, loc.program)
                        if src_type is not None and _is_downcast(src_type.name, target_type.name):
                            result.append(Diagnostic(
                                code=WS105.code, severity=WS105.severity,
                                location=loc,
                                message=WS105(
                                    name=target_name,
                                    from_type=src_type.name,
                                    to_type=target_type.name,
                                ).message,
                            ))
    return result
