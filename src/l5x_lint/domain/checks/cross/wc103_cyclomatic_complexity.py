from l5x_lint.domain.checks._codes import WC103
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StCase, StFor, StIf, StProgram, StWhile
from l5x_lint.application.analyze import register
from l5x_lint.domain.symbols import SymbolTable

_THRESHOLD = 15


def _count_st_branches(stmt) -> int:
    count = 0
    match stmt:
        case StIf():
            count += 1
            for s in stmt.body:
                count += _count_st_branches(s)
            for _, body in stmt.elsif_pairs:
                count += 1
                for s in body:
                    count += _count_st_branches(s)
            for s in stmt.else_body:
                count += _count_st_branches(s)
        case StCase():
            count += 1
            for _, body in stmt.cases:
                for s in body:
                    count += _count_st_branches(s)
            for s in stmt.else_body:
                count += _count_st_branches(s)
        case StFor() | StWhile():
            count += 1
            body = stmt.body if hasattr(stmt, "body") else []
            for s in body:
                count += _count_st_branches(s)
        case _:
            pass
    return count


@register
def wc103_cyclomatic_complexity(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    if routine.type == "ST":
        bod = routine.st_body
        if isinstance(bod, StProgram):
            total = 0
            for stmt in bod.statements:
                total += _count_st_branches(stmt)
            if total >= _THRESHOLD:
                result.append(
                    Diagnostic(
                        code=WC103.code,
                        severity=WC103.severity,
                        location=loc,
                        message=WC103(complexity=total, threshold=_THRESHOLD).message,
                    )
                )
    if routine.type == "RLL":
        branch_count = 0
        for rung in routine.rll_rungs:
            for inst in rung.instructions:
                if inst.opcode.upper() in ("XIC", "XIO", "OTE", "OTL", "OTU"):
                    branch_count += 1
                if inst.branch:
                    for path in inst.branch:
                        for bi in path:
                            if bi.opcode.upper() in ("XIC", "XIO", "OTE", "OTL", "OTU"):
                                branch_count += 1
        if branch_count >= _THRESHOLD:
            result.append(
                Diagnostic(
                    code=WC103.code,
                    severity=WC103.severity,
                    location=loc,
                    message=WC103(
                        complexity=branch_count, threshold=_THRESHOLD
                    ).message,
                )
            )
    return result
