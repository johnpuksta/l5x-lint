from collections.abc import Callable

from returns.pipeline import flow
from returns.pointfree import bind
from returns.result import Result, Success

from l5x_lint.domain.diagnostics import AnalysisResult, Diagnostic
from l5x_lint.domain.errors import LintInternalError
from l5x_lint.domain.models import Controller, Location, Routine
from l5x_lint.pipeline.routine_router import route_routines
from l5x_lint.pipeline.symbols import SymbolTable, build_symbol_table

CheckFn = Callable[[Routine, SymbolTable, Location], list[Diagnostic]]

_registry: list[CheckFn] = []


def register(check: CheckFn) -> CheckFn:
    _registry.append(check)
    return check


def analyze(controller: Controller) -> Result[AnalysisResult, LintInternalError]:
    return flow(
        Success(controller),
        bind(route_routines),
        bind(_run_checks),
    )


def _run_checks(controller: Controller) -> Result[AnalysisResult, LintInternalError]:
    symbols = build_symbol_table(controller)
    diagnostics: list[Diagnostic] = []

    for prog in controller.programs:
        for r in prog.routines:
            loc = Location(program=prog.name, routine=r.name)
            for check in _registry:
                diagnostics.extend(check(r, symbols, loc))

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = sum(1 for d in diagnostics if d.severity == "warning")
    return Success(AnalysisResult(
        passed=errors == 0,
        error_count=errors,
        warning_count=warnings,
        diagnostics=diagnostics,
    ))
