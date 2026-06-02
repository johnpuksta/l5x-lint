import re

from application.analyze import register
from domain.checks._codes import WS102
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.symbols import SymbolTable

_ZERO_DIV_RE = re.compile(r"/\s*0\b")
_ZERO_MOD_RE = re.compile(r"\bMOD\s+0\b", re.IGNORECASE)


@register
def ws102_div_by_zero(
    routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    if routine.type == "ST" and routine.cdata:
        for i, line in enumerate(routine.cdata.splitlines(), 1):
            stripped = line.strip()
            if _ZERO_DIV_RE.search(stripped) or _ZERO_MOD_RE.search(stripped):
                result.append(
                    Diagnostic(
                        code=WS102.code,
                        severity=WS102.severity,
                        location=Location(
                            program=loc.program, routine=loc.routine, line=i
                        ),
                        message=WS102(text=stripped).message,
                    )
                )
    if routine.type == "RLL":
        for rung in routine.rll_rungs:
            for inst in rung.instructions:
                if inst.opcode.upper() in ("DIV", "MOD", "CPT"):
                    for op in inst.operands:
                        if _ZERO_DIV_RE.search(op.value) or _ZERO_MOD_RE.search(
                            op.value
                        ):
                            result.append(
                                Diagnostic(
                                    code=WS102.code,
                                    severity=WS102.severity,
                                    location=Location(
                                        program=loc.program,
                                        routine=loc.routine,
                                        rung=rung.number,
                                    ),
                                    message=WS102(
                                        text=f"{inst.opcode}({op.value})"
                                    ).message,
                                )
                            )
    return result
