from l5x_lint.domain.diagnostics import (
    AnalysisResult,
    Diagnostic,
    FixSuggestion,
    RelatedInfo,
)
from l5x_lint.domain.models import Location


def test_diagnostic_minimal():
    loc = Location("P", "R", rung=0)
    d = Diagnostic("EC001", "error", loc, "Undefined tag")
    assert d.code == "EC001"
    assert d.severity == "error"
    assert d.hint is None
    assert d.fix_suggestion is None
    assert d.related == []
    assert d.iec_reference is None


def test_diagnostic_with_related():
    loc = Location("P", "R", rung=0)
    related_loc = Location("P", "R2", rung=1)
    d = Diagnostic(
        "EC007",
        "error",
        loc,
        "Duplicate tag",
        related=[RelatedInfo(related_loc, "Previously declared here")],
    )
    assert len(d.related) == 1
    assert d.related[0].message == "Previously declared here"
    assert d.related[0].location.rung == 1


def test_diagnostic_with_iec_ref():
    loc = Location("P", "R")
    d = Diagnostic(
        "WS101", "warning", loc, "Float eq", iec_reference="IEC 61131-3 §6.3.2"
    )
    assert d.iec_reference == "IEC 61131-3 §6.3.2"


def test_diagnostic_with_hint():
    loc = Location("P", "R", rung=0)
    d = Diagnostic(
        "EC001", "error", loc, "Undefined tag", hint="Did you mean 'Motor_Run'?"
    )
    assert d.hint is not None


def test_analysis_result_passed():
    r = AnalysisResult(passed=True, error_count=0, warning_count=0)
    assert r.passed
    assert r.error_count == 0


def test_analysis_result_failed():
    diag = Diagnostic(Location("P", "R"), "EC001", "error", "bad")
    r = AnalysisResult(passed=False, error_count=1, warning_count=0, diagnostics=[diag])
    assert not r.passed
    assert len(r.diagnostics) == 1


def test_fix_suggestion_minimal():
    f = FixSuggestion("EC001", "Add missing tag")
    assert f.code == "EC001"
    assert f.replacement is None


def test_fix_suggestion_full():
    f = FixSuggestion("EC001", "Rename tag", target_tag="Motor_Run")
    assert f.target_tag == "Motor_Run"
