from l5x_lint.checks._codes import EC004
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StJsr
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def ec004_invalid_subroutine(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    valid_routines = symbols.routine_names
    result: list[Diagnostic] = []

    if routine.type == "RLL":
        for rung in routine.rll_rungs:
            for inst in rung.instructions:
                if inst.opcode.upper() in ("JSR", "JXR"):
                    if inst.operands and inst.operands[0].value not in valid_routines:
                        result.append(
                            Diagnostic(
                                code=EC004.code,
                                severity=EC004.severity,
                                location=Location(
                                    program=loc.program, routine=loc.routine, rung=rung.number
                                ),
                                message=EC004(routine=inst.operands[0].value).message,
                            )
                        )

    if routine.type == "ST" and hasattr(routine.st_body, "statements"):
        for stmt in routine.st_body.statements:
            if isinstance(stmt, StJsr):
                if stmt.routine_name not in valid_routines:
                    result.append(
                        Diagnostic(
                            code=EC004.code,
                            severity=EC004.severity,
                            location=loc,
                            message=EC004(routine=stmt.routine_name).message,
                        )
                    )

    return result
