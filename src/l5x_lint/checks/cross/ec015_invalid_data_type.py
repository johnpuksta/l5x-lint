from l5x_lint.checks._codes import EC015
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.domain.symbols import SymbolTable

_BUILTIN_TYPES: frozenset[str] = frozenset(
    {
        "BOOL",
        "SINT",
        "INT",
        "DINT",
        "LINT",
        "USINT",
        "UINT",
        "UDINT",
        "ULINT",
        "REAL",
        "LREAL",
        "STRING",
        "TIMER",
        "COUNTER",
        "CONTROL",
    }
)

_processed: bool = False
_reported: set[str] = set()


def _reset():
    global _processed, _reported
    _processed = False
    _reported.clear()


@register
def ec015_invalid_data_type(
    _routine: Routine,
    symbols: SymbolTable,
    loc: Location,
) -> list[Diagnostic]:
    global _processed, _reported
    result: list[Diagnostic] = []
    if _processed:
        return result
    _processed = True

    valid_types: set[str] = set(symbols.data_types.keys()) | _BUILTIN_TYPES

    for tag in symbols.controller_tags.values():
        if tag.data_type and tag.data_type not in valid_types:
            _check_report(tag.name, tag.data_type, loc, result)

    for prog_name, tags in symbols.program_tags.items():
        prog_loc = Location(program=prog_name, routine=loc.routine)
        for tag in tags.values():
            if tag.data_type and tag.data_type not in valid_types:
                _check_report(tag.name, tag.data_type, prog_loc, result)

    return result


def _check_report(
    tag_name: str,
    data_type: str,
    loc: Location,
    result: list[Diagnostic],
):
    key = f"{tag_name}:{data_type}"
    if key in _reported:
        return
    _reported.add(key)
    result.append(
        Diagnostic(
            code=EC015.code,
            severity=EC015.severity,
            location=loc,
            message=EC015(tag_name=tag_name, data_type=data_type).message,
        )
    )
