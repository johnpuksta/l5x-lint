from returns.result import Success

from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Controller, Program, Routine, Tag
from l5x_lint.pipeline import analyze


def _reset_registry():
    analyze._registry.clear()


def test_empty_controller():
    _reset_registry()
    result = analyze.analyze(Controller(name="Test"))
    assert isinstance(result, Success)
    ar = result.unwrap()
    assert ar.passed
    assert ar.diagnostics == []


def test_no_checks_registered():
    _reset_registry()
    c = Controller(
        name="Test",
        programs=[
            Program(name="Prog", routines=[Routine(name="Main", type="RLL")]),
        ],
    )
    result = analyze.analyze(c)
    assert isinstance(result, Success)
    assert result.unwrap().diagnostics == []


def test_check_collects_diagnostics():
    _reset_registry()

    def _demo_check(routine, symbols, location):
        return [
            Diagnostic(
                code="DEMO", severity="error", location=location, message="test"
            ),
        ]

    analyze.register(_demo_check)
    c = Controller(
        name="Test",
        programs=[
            Program(name="Prog", routines=[Routine(name="Main", type="RLL")]),
        ],
    )
    result = analyze.analyze(c)
    assert isinstance(result, Success)
    ar = result.unwrap()
    assert not ar.passed
    assert ar.error_count == 1
    assert len(ar.diagnostics) == 1
    assert ar.diagnostics[0].location.program == "Prog"
    assert ar.diagnostics[0].location.routine == "Main"


def test_multiple_routines():
    _reset_registry()

    def _demo_check(routine, symbols, location):
        return [
            Diagnostic(
                code="DEMO", severity="warning", location=location,
                message=str(routine.name),
            ),
        ]

    analyze.register(_demo_check)
    c = Controller(
        name="Test",
        programs=[
            Program(
                name="Prog",
                routines=[
                    Routine(name="R1", type="RLL"),
                    Routine(name="R2", type="ST"),
                ],
            ),
        ],
    )
    result = analyze.analyze(c)
    ar = result.unwrap()
    assert ar.warning_count == 2
    msgs = {d.message for d in ar.diagnostics}
    assert msgs == {"R1", "R2"}


def test_multiple_programs():
    _reset_registry()

    def _demo_check(routine, symbols, location):
        return [
            Diagnostic(code="DEMO", severity="error", location=location, message="err"),
        ]

    analyze.register(_demo_check)
    c = Controller(
        name="Test",
        programs=[
            Program(name="A", routines=[Routine(name="R1", type="RLL")]),
            Program(name="B", routines=[Routine(name="R2", type="ST")]),
        ],
    )
    result = analyze.analyze(c)
    ar = result.unwrap()
    assert ar.error_count == 2
    progs = {d.location.program for d in ar.diagnostics}
    assert progs == {"A", "B"}


def test_mixed_severity():
    _reset_registry()

    def _demo_check(routine, symbols, location):
        return [
            Diagnostic(code="EC001", severity="error", location=location, message="e"),
            Diagnostic(code="WC001", severity="warning", location=location, message="w"),
        ]

    analyze.register(_demo_check)
    c = Controller(
        name="Test",
        programs=[
            Program(name="Prog", routines=[Routine(name="Main", type="RLL")]),
        ],
    )
    result = analyze.analyze(c)
    ar = result.unwrap()
    assert ar.error_count == 1
    assert ar.warning_count == 1
    assert not ar.passed


def test_all_warnings_still_passes():
    _reset_registry()

    def _demo_check(routine, symbols, location):
        return [
            Diagnostic(code="WC001", severity="warning", location=location, message="w"),
        ]

    analyze.register(_demo_check)
    c = Controller(
        name="Test",
        programs=[
            Program(name="Prog", routines=[Routine(name="Main", type="RLL")]),
        ],
    )
    result = analyze.analyze(c)
    ar = result.unwrap()
    assert ar.passed
    assert ar.warning_count == 1
    assert ar.error_count == 0


def test_check_receives_symbols():
    _reset_registry()
    captured_table = None

    def _capture_check(routine, symbols, location):
        nonlocal captured_table
        captured_table = symbols
        return []

    analyze.register(_capture_check)
    c = Controller(
        name="Test",
        tags=[Tag(name="MyTag", data_type="DINT")],
        programs=[
            Program(name="Prog", routines=[Routine(name="Main", type="RLL")]),
        ],
    )
    analyze.analyze(c)
    assert captured_table is not None
    assert "MyTag" in captured_table.controller_tags
