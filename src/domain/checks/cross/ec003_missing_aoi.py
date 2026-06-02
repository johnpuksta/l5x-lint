"""EC003: Missing AOI definition.

Uses _BUILTIN_OPCODES to distinguish built-in instructions from AOIs.
Any opcode not in this set and not defined as an AOI triggers EC003.
Must stay in sync with OPCODE_OPERANDS in opcodes.py.
"""

from application._registry import register
from domain.checks._codes import EC003
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.st_models import StCall
from domain.symbols import SymbolTable

_BUILTIN_OPCODES: frozenset[str] = frozenset(
    {
        "JSR",
        "JXR",
        "XIC",
        "XIO",
        "OTE",
        "OTL",
        "OTU",
        "TON",
        "TOF",
        "RTO",
        "CTU",
        "CTD",
        "ADD",
        "SUB",
        "MUL",
        "DIV",
        "MOV",
        "CLR",
        "CPT",
        "EQU",
        "NEQ",
        "LES",
        "LEQ",
        "GRT",
        "GEQ",
        "GT",
        "RES",
        "PID",
        "MSG",
        "GSV",
        "SSV",
        "COP",
        "CPS",
        "FAL",
        "FSC",
        "MCR",
        "JMP",
        "LBL",
        "AFI",
        "NOP",
        "TND",
        "BST",
        "BND",
        "NXB",
        "ONS",
        "OSR",
        "OSF",
        "SCL",
        "CPW",
        "SWPB",
        "MOD",
        "NEG",
        "SQR",
        "ABS",
        "CMP",
        "LIM",
        "IOT",
        "SFP",
        "SFR",
        "DTOS",
        "STOD",
        "SPP",
        "SRT",
    }
)


@register
def ec003_missing_aoi(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    if routine.type == "RLL":
        for rung in routine.rll_rungs:
            _check_rll(rung.instructions, symbols, loc, rung.number, result)

    if routine.type == "ST" and hasattr(routine.st_body, "statements"):
        for stmt in routine.st_body.statements:
            if isinstance(stmt, StCall):
                name = stmt.name.upper()
                if name not in _BUILTIN_OPCODES and stmt.name not in symbols.aoi_names:
                    result.append(
                        Diagnostic(
                            code=EC003.code,
                            severity=EC003.severity,
                            location=loc,
                            message=EC003(name=stmt.name).message,
                        )
                    )

    return result


def _check_rll(instructions, symbols, loc, rung_num, result):
    for inst in instructions:
        opcode = inst.opcode.upper()
        if opcode not in _BUILTIN_OPCODES and inst.opcode not in symbols.aoi_names:
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
                _check_rll(path, symbols, loc, rung_num, result)
