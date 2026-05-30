from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.domain.models import Location
from l5x_lint.pipeline.config import LintConfig
from l5x_lint.pipeline.filter import filter_diagnostics


_LOC = Location("Prog", "Main", rung=0)


def test_no_config_returns_all():
    c = LintConfig()
    diags = [
        Diagnostic("EC001", "error", _LOC, "err"),
        Diagnostic("WC001", "warning", _LOC, "warn"),
    ]
    result = filter_diagnostics(diags, c)
    assert result == diags


def test_suppresses_disabled_warning():
    c = LintConfig(warn_unused=False)
    d1 = Diagnostic("EC001", "error", _LOC, "err")
    d2 = Diagnostic("WC001", "warning", _LOC, "warn")
    result = filter_diagnostics([d1, d2], c)
    assert len(result) == 1
    assert result[0].code == "EC001"


def test_severity_override_off():
    c = LintConfig()
    c.severity_overrides = {"WC001": "off"}
    d = Diagnostic("WC001", "warning", _LOC, "warn")
    result = filter_diagnostics([d], c)
    assert result == []


def test_severity_override_promote():
    c = LintConfig()
    c.severity_overrides = {"WC001": "error"}
    d = Diagnostic("WC001", "warning", _LOC, "warn")
    result = filter_diagnostics([d], c)
    assert len(result) == 1
    assert result[0].severity == "error"


def test_numeric_hazard_suppressed_by_default():
    c = LintConfig()
    d = Diagnostic("WS101", "warning", _LOC, "float eq")
    result = filter_diagnostics([d], c)
    assert result == []


def test_numeric_hazard_enabled():
    c = LintConfig(warn_numeric_hazards=True)
    d = Diagnostic("WS101", "warning", _LOC, "float eq")
    result = filter_diagnostics([d], c)
    assert len(result) == 1
