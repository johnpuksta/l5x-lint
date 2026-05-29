from l5x_lint.checks._codes import E007
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def e007_duplicate_tag(
    _routine: Routine, symbols: SymbolTable, _loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    for name in symbols.duplicate_controller_tags:
        result.append(
            Diagnostic(
                code=E007.code,
                severity=E007.severity,
                location=Location(program="controller", routine=""),
                message=E007(name=name, scope="controller").message,
            )
        )

    for prog_name, dupes in symbols.duplicate_program_tags.items():
        for name in dupes:
            result.append(
                Diagnostic(
                    code=E007.code,
                    severity=E007.severity,
                    location=Location(program=prog_name, routine=""),
                    message=E007(name=name, scope=prog_name).message,
                )
            )

    return result
