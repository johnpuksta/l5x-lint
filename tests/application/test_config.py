from application.config import LintConfig


def test_default_config():
    c = LintConfig()
    assert c.warn_unused
    assert c.warn_unreachable
    assert c.warn_output_never_driven
    assert c.warn_timer_pre
    assert c.warn_shadowed
    assert not c.warn_numeric_hazards
    assert not c.warn_complexity
    assert c.warn_implicit_conversion
    assert c.warn_missing_else
    assert c.rule_pack == "none"
    assert c.dialect == "rockwell"


def test_diagnostic_allowed_default():
    c = LintConfig()
    assert c.diagnostic_allowed("WC001")
    assert c.diagnostic_allowed("WR002")
    assert c.diagnostic_allowed("WR003")
    assert c.diagnostic_allowed("WR004")
    assert c.diagnostic_allowed("WC005")
    assert not c.diagnostic_allowed("WS101")
    assert not c.diagnostic_allowed("WS102")
    assert c.diagnostic_allowed("WS104")
    assert c.diagnostic_allowed("WS105")
    assert c.diagnostic_allowed("WS107")
    assert not c.diagnostic_allowed("WC103")
    assert c.diagnostic_allowed("EC001")
    assert c.diagnostic_allowed("ER013")


def test_enable_numeric_hazards():
    c = LintConfig()
    c.warn_numeric_hazards = True
    assert c.diagnostic_allowed("WS101")
    assert c.diagnostic_allowed("WS102")


def test_enable_complexity():
    c = LintConfig()
    c.warn_complexity = True
    assert c.diagnostic_allowed("WC103")


def test_disable_warning():
    c = LintConfig()
    c.warn_unreachable = False
    assert not c.diagnostic_allowed("WR002")
    assert not c.diagnostic_allowed("WS110")


def test_severity_resolve():
    c = LintConfig()
    c.severity_overrides = {"WS101": "error", "WR004": "off"}
    assert c.resolve_severity("WS101", "warning") == "error"
    assert c.resolve_severity("WR004", "warning") == "off"
    assert c.resolve_severity("WC001", "warning") == "warning"


def test_rule_pack_none():
    c = LintConfig(rule_pack="none")
    c.apply_rule_pack()
    assert not c.warn_numeric_hazards
    assert not c.warn_complexity


def test_rule_pack_safety():
    c = LintConfig(rule_pack="safety")
    c.apply_rule_pack()
    assert c.warn_numeric_hazards
    assert c.warn_unreachable
    assert c.severity_overrides["WC103"] == "error"
    assert c.severity_overrides["WR002"] == "error"


def test_rule_pack_iec():
    c = LintConfig(rule_pack="iec-61131-3")
    c.apply_rule_pack()
    assert c.warn_output_never_driven
    assert c.warn_complexity
    assert c.warn_missing_else
