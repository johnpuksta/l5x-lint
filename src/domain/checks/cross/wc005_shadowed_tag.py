from application._registry import register
from domain.checks._codes import WC005
from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
from domain.symbols import SymbolTable


@register
def wc005_shadowed_tag(
    _routine: Routine,
    symbols: SymbolTable,
    _loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []
    for prog_name, tags in symbols.program_tags.items():
        for tag_name in tags:
            if tag_name in symbols.controller_tags:
                result.append(
                    Diagnostic(
                        code=WC005.code,
                        severity=WC005.severity,
                        location=Location(program=prog_name, routine=""),
                        message=WC005(name=tag_name, hidden_by=tag_name).message,
                    )
                )
    return result
