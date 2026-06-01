from l5x_lint.checks._codes import EC016
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.domain.symbols import SymbolTable

_reported: set[str] = set()


def _reset():
    _reported.clear()


@register
def ec016_invalid_array_range(
    _routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    for name, tag in symbols.controller_tags.items():
        if name in _reported:
            continue
        for dim in tag.dimensions:
            if dim <= 0:
                _reported.add(name)
                result.append(
                    Diagnostic(
                        code=EC016.code,
                        severity=EC016.severity,
                        location=loc,
                        message=EC016(name=name, dim=dim).message,
                    )
                )

    for prog_name, tags in symbols.program_tags.items():
        prog_loc = Location(program=prog_name, routine=loc.routine)
        for name, tag in tags.items():
            if name in _reported:
                continue
            for dim in tag.dimensions:
                if dim <= 0:
                    _reported.add(name)
                    result.append(
                        Diagnostic(
                            code=EC016.code,
                            severity=EC016.severity,
                            location=prog_loc,
                            message=EC016(name=name, dim=dim).message,
                        )
                    )

    return result
