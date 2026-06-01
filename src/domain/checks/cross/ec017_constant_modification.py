from domain.checks._codes import EC017
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.st_models import StAssignment, StProgram
from application.analyze import register
from domain.symbols import SymbolTable

_REPORTED_OUTPUTS: set[str] = set()


def _reset():
    _REPORTED_OUTPUTS.clear()


@register
def ec017_constant_modification(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    bod = routine.st_body
    if isinstance(bod, StProgram):
        for stmt in bod.statements:
            _check_st_assignment(stmt, symbols, loc, result)

    if routine.type == "RLL" and routine.rll_rungs:
        _check_rll_outputs(routine.rll_rungs, symbols, loc, result)

    return result


def _check_st_assignment(
    stmt, symbols: SymbolTable, loc: Location, result: list[Diagnostic]
):
    match stmt:
        case StAssignment():
            tag_name = stmt.target.segments[0].name if stmt.target.segments else ""
            if _is_constant_tag(tag_name, loc.program, symbols):
                result.append(
                    Diagnostic(
                        code=EC017.code,
                        severity=EC017.severity,
                        location=Location(
                            program=loc.program,
                            routine=loc.routine,
                            line=stmt.line,
                        ),
                        message=EC017(name=tag_name).message,
                    )
                )


def _check_rll_outputs(
    rungs, symbols: SymbolTable, loc: Location, result: list[Diagnostic]
):
    for rung in rungs:
        _walk_rll_instructions(rung.instructions, symbols, loc, result)


def _walk_rll_instructions(
    instructions, symbols: SymbolTable, loc: Location, result: list[Diagnostic]
):
    for inst in instructions:
        opcode = inst.opcode.upper()
        if opcode in ("OTE", "OTL", "OTU") and inst.operands:
            tag_name = inst.operands[0].value
            if _is_constant_tag(tag_name, loc.program, symbols):
                if tag_name not in _REPORTED_OUTPUTS:
                    _REPORTED_OUTPUTS.add(tag_name)
                    result.append(
                        Diagnostic(
                            code=EC017.code,
                            severity=EC017.severity,
                            location=loc,
                            message=EC017(name=tag_name).message,
                        )
                    )
        if inst.branch:
            for path in inst.branch:
                _walk_rll_instructions(path, symbols, loc, result)


def _is_constant_tag(name: str, program: str, symbols: SymbolTable) -> bool:
    from returns.maybe import Some

    match symbols.resolve(name, program):
        case Some(tag):
            return tag.constant
        case _:
            return False
