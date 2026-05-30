from l5x_lint.checks._codes import EC012
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable

_reported: set[str] = set()


def _reset():
    _reported.clear()


@register
def ec012_array_init_count(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    for name, tag in symbols.controller_tags.items():
        if name in _reported:
            continue
        if not tag.dimensions or tag.initial_values is None:
            continue
        expected = 1
        for d in tag.dimensions:
            expected *= d
        if tag.initial_values != expected:
            _reported.add(name)
            result.append(Diagnostic(
                code=EC012.code, severity=EC012.severity,
                location=loc,
                message=EC012(
                    name=name, expected=expected, actual=tag.initial_values,
                ).message,
            ))

    for prog_name, tags in symbols.program_tags.items():
        for name, tag in tags.items():
            if name in _reported:
                continue
            if not tag.dimensions or tag.initial_values is None:
                continue
            expected = 1
            for d in tag.dimensions:
                expected *= d
            if tag.initial_values != expected:
                _reported.add(name)
                result.append(Diagnostic(
                    code=EC012.code, severity=EC012.severity,
                    location=loc,
                    message=EC012(
                        name=name, expected=expected, actual=tag.initial_values,
                    ).message,
                ))

    return result
