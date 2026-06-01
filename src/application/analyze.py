from __future__ import annotations

from collections.abc import Callable

from returns.pipeline import flow
from returns.pointfree import bind
from returns.result import Result, Success

from domain.diagnostics import AnalysisResult, Diagnostic
from domain.errors import LintInternalError
from domain.models import Controller, Location, Routine
from application.config import LintConfig
from application.filter import filter_diagnostics
from application.routine_router import route_routines
from domain.symbols import SymbolTable, build_symbol_table

CheckFn = Callable[[Routine, SymbolTable, Location], list[Diagnostic]]

_registry: list[CheckFn] = []


def register(check: CheckFn) -> CheckFn:
    _registry.append(check)
    return check


def analyze(
    controller: Controller,
    config: LintConfig | None = None,
) -> Result[AnalysisResult, LintInternalError]:
    if config is not None:
        config.apply_rule_pack()
        config.apply_dialect_preset()
    result = flow(
        Success(controller),
        bind(route_routines),
        bind(_run_checks),
    )
    match result:
        case Success(ar) if config is not None:
            filtered = filter_diagnostics(ar.diagnostics, config)
            errors = sum(1 for d in filtered if d.severity == "error")
            warnings = sum(1 for d in filtered if d.severity == "warning")
            return Success(
                AnalysisResult(
                    passed=errors == 0,
                    error_count=errors,
                    warning_count=warnings,
                    diagnostics=filtered,
                )
            )
        case _:
            return result


def _run_checks(controller: Controller) -> Result[AnalysisResult, LintInternalError]:
    symbols = build_symbol_table(controller)
    diagnostics: list[Diagnostic] = []

    for prog in controller.programs:
        for r in prog.routines:
            loc = Location(program=prog.name, routine=r.name)
            for check in _registry:
                try:
                    diagnostics.extend(check(r, symbols, loc))
                except Exception as e:
                    name = getattr(check, "__name__", type(check).__name__)
                    diagnostics.append(
                        Diagnostic(
                            code="EX101",
                            severity="error",
                            message=f"Check '{name}' crashed: {e}",
                            location=loc,
                        )
                    )

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = sum(1 for d in diagnostics if d.severity == "warning")
    return Success(
        AnalysisResult(
            passed=errors == 0,
            error_count=errors,
            warning_count=warnings,
            diagnostics=diagnostics,
        )
    )
