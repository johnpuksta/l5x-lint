from l5x_lint.checks.tag_refs import extract_base
from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.errors import E010
from l5x_lint.domain.models import Location, Routine
from l5x_lint.pipeline.analyze import register
from l5x_lint.pipeline.symbols import SymbolTable


@register
def e010_cross_scope(
    routine: Routine, symbols: SymbolTable, loc: Location,
) -> list[Diagnostic]:
    result: list[Diagnostic] = []

    if routine.type == "RLL":
        for rung in routine.rll_rungs:
            _check_rll(rung.instructions, symbols, loc, rung.number, result)

    if routine.type == "ST" and hasattr(routine.st_body, "statements"):
        from l5x_lint.checks.tag_refs import st_tag_refs
        names = st_tag_refs(routine)
        for name in names:
            if symbols.tag_in_other_program(name, loc.program):
                declared_in = _find_program_for_tag(symbols, name, loc.program)
                if declared_in:
                    result.append(
                        Diagnostic(
                            code=E010.code,
                            severity=E010.severity,
                            location=loc,
                            message=E010(
                                name=name,
                                accessed_from=loc.program,
                                declared_in=declared_in,
                            ).message,
                        )
                    )

    return result


def _check_rll(instructions, symbols, loc, rung_num, result):
    for inst in instructions:
        for op in inst.operands:
            base = extract_base(op.value)
            if base is not None and symbols.tag_in_other_program(base, loc.program):
                declared_in = _find_program_for_tag(symbols, base, loc.program)
                if declared_in:
                    result.append(
                        Diagnostic(
                            code=E010.code,
                            severity=E010.severity,
                            location=loc,
                            message=E010(
                                name=base,
                                accessed_from=loc.program,
                                declared_in=declared_in,
                            ).message,
                        )
                    )
        if inst.branch:
            for path in inst.branch:
                _check_rll(path, symbols, loc, rung_num, result)


def _find_program_for_tag(symbols: SymbolTable, name: str, exclude: str) -> str | None:
    for prog_name, tags in symbols.program_tags.items():
        if prog_name != exclude and name in tags:
            return prog_name
    return None
