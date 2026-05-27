from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.errors import E007
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def e007_duplicate_tag(
    _routine: Routine, symbols: SymbolTable, _loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    names = {t.name for t in symbols.controller_tags.values()}
    if len(names) != len(symbols.controller_tags):
        seen: set[str] = set()
        for t in symbols.controller_tags.values():
            if t.name in seen:
                result.append(
                    Diagnostic(
                        code=E007.code,
                        severity=E007.severity,
                        location=Location(program="controller", routine=""),
                        message=E007(name=t.name, scope="controller").message,
                    )
                )
            else:
                seen.add(t.name)

    for prog_name, tags in symbols.program_tags.items():
        if len(set(tags.keys())) != len(tags):
            seen = set()
            for tag_name in tags:
                if tag_name in seen:
                    result.append(
                        Diagnostic(
                            code=E007.code,
                            severity=E007.severity,
                            location=Location(program=prog_name, routine=""),
                            message=E007(name=tag_name, scope=prog_name).message,
                        )
                    )
                else:
                    seen.add(tag_name)

    return result
