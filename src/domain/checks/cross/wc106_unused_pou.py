from application._registry import register
from domain.checks._codes import WC106
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.symbols import SymbolTable

_used_aois: set[str] = set()
_used_programs: set[str] = set()
_done: bool = False


def _reset():
    global _used_aois, _used_programs, _done
    _used_aois.clear()
    _used_programs.clear()
    _done = False


@register
def wc106_unused_pou(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    global _used_aois, _used_programs, _done
    result: list[Diagnostic] = []

    if not _done:
        for aoi in symbols.aoi_list:
            pass
        _done = True

    if routine.type == "RLL":
        for rung in routine.rll_rungs:
            for inst in rung.instructions:
                if inst.opcode.upper() == "JSR":
                    _used_programs.add("dummy")
                if inst.opcode.upper() not in (
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
                    "SUS",
                    "IOT",
                    "SPP",
                    "SRT",
                    "SFP",
                    "SFR",
                    "DTOS",
                    "STOD",
                ):
                    _used_aois.add(inst.opcode)

    if routine.type == "ST":
        bod = routine.st_body
        if bod is not None:
            from domain.st_models import StCall, StJsr

            for stmt in bod.statements:
                match stmt:
                    case StCall():
                        if stmt.name.upper() not in (
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
                        ):
                            _used_aois.add(stmt.name)
                    case StJsr():
                        _used_programs.add("dummy")

    unused = set()
    for aoi_name in symbols.aoi_names:
        if aoi_name not in _used_aois:
            unused.add(aoi_name)
            result.append(
                Diagnostic(
                    code=WC106.code,
                    severity=WC106.severity,
                    location=loc,
                    message=WC106(name=aoi_name, kind="AOI").message,
                )
            )
    return result
