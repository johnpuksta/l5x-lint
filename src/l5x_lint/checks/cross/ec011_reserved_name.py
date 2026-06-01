from l5x_lint.checks._codes import EC011
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable

_RESERVED_NAMES: frozenset[str] = frozenset(
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
        "DDT",
        "SDT",
        "SFC",
        "FBC",
        "TRN",
        "REF",
        "IOT",
        "SPP",
        "SRT",
        "SFP",
        "SFR",
        "DTOS",
        "STOD",
    }
)


_reported: set[str] = set()


def _reset():
    _reported.clear()


@register
def ec011_reserved_name(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    global _reported
    result: list[Diagnostic] = []
    for name in symbols.aoi_names:
        if name.upper() in _RESERVED_NAMES and name not in _reported:
            _reported.add(name)
            result.append(
                Diagnostic(
                    code=EC011.code,
                    severity=EC011.severity,
                    location=loc,
                    message=EC011(name=name, kind="AOI").message,
                )
            )
    for prog_name in symbols.program_tags:
        if prog_name.upper() in _RESERVED_NAMES and prog_name not in _reported:
            _reported.add(prog_name)
            result.append(
                Diagnostic(
                    code=EC011.code,
                    severity=EC011.severity,
                    location=loc,
                    message=EC011(name=prog_name, kind="Program").message,
                )
            )
    return result
