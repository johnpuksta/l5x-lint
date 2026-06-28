"""EC003: Missing AOI definition.

Uses builtin_opcodes() to distinguish built-in instructions from AOIs.
Any opcode not in this set and not defined as an AOI triggers EC003.
Version-aware: v36+ aliases (EQ, NE, LT, LE, GE, MOVE) are only
accepted for projects with SoftwareRevision >= 36.
"""

from application._registry import register
from domain.checks._codes import EC003
from domain.checks._opcode_sets import builtin_opcodes, resolve_opcode
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.st_models import StCall
from domain.symbols import SymbolTable


@register
def ec003_missing_aoi(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    opcodes = builtin_opcodes(symbols.software_revision)

    if routine.type == "RLL":
        for rung in routine.rll_rungs:
            _check_rll(rung.instructions, symbols, loc, rung.number, opcodes, result)

    if routine.type == "ST" and hasattr(routine.st_body, "statements"):
        for stmt in routine.st_body.statements:
            if isinstance(stmt, StCall):
                canonical = resolve_opcode(stmt.name, symbols.software_revision)
                if canonical not in opcodes and stmt.name not in symbols.aoi_names:
                    result.append(
                        Diagnostic(
                            code=EC003.code,
                            severity=EC003.severity,
                            location=loc,
                            message=EC003(name=stmt.name).message,
                        )
                    )

    return result


def _check_rll(instructions, symbols, loc, rung_num, opcodes, result):
    for inst in instructions:
        canonical = resolve_opcode(inst.opcode, symbols.software_revision)
        if canonical not in opcodes and inst.opcode not in symbols.aoi_names:
            result.append(
                Diagnostic(
                    code=EC003.code,
                    severity=EC003.severity,
                    location=Location(
                        program=loc.program, routine=loc.routine, rung=rung_num
                    ),
                    message=EC003(name=inst.opcode).message,
                )
            )
        if inst.branch:
            for path in inst.branch:
                _check_rll(path, symbols, loc, rung_num, opcodes, result)
