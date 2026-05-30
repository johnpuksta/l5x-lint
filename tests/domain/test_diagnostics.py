from l5x_lint.domain.diagnostics import AnalysisResult, Diagnostic, FixSuggestion
from l5x_lint.domain.models import Location


def test_diagnostic_minimal():
    loc = Location("P", "R", rung=0)
    d = Diagnostic("EC001", "error", loc, "Undefined tag")
    assert d.code == "EC001"
    assert d.severity == "error"
    assert d.hint is None
    assert d.fix_suggestion is None


def test_diagnostic_with_hint():
    loc = Location("P", "R", rung=0)
    d = Diagnostic("EC001", "error", loc, "Undefined tag",
                    hint="Did you mean 'Motor_Run'?")
    assert d.hint is not None


def test_analysis_result_passed():
    r = AnalysisResult(passed=True, error_count=0, warning_count=0)
    assert r.passed
    assert r.error_count == 0


def test_analysis_result_failed():
    diag = Diagnostic(Location("P", "R"), "EC001", "error", "bad")
    r = AnalysisResult(passed=False, error_count=1, warning_count=0,
                       diagnostics=[diag])
    assert not r.passed
    assert len(r.diagnostics) == 1


def test_fix_suggestion_minimal():
    f = FixSuggestion("EC001", "Add missing tag")
    assert f.code == "EC001"
    assert f.replacement is None


def test_fix_suggestion_full():
    f = FixSuggestion("EC001", "Rename tag", target_tag="Motor_Run")
    assert f.target_tag == "Motor_Run"
