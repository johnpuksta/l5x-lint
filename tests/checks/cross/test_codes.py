from l5x_lint.checks._codes import (
    EC001,
    EC002,
    EC003,
    EC004,
    EC005,
    EC006,
    EC007,
    EC008,
    EC010,
    EC011,
    EC012,
    ER009,
    WC001,
    WC005,
    WC103,
    WC106,
    WR002,
    WR003,
    WR004,
    WS101,
    WS102,
    WS104,
    WS105,
    WS107,
    LintError,
)


def assert_error_common(e, code, severity):
    assert e.code == code
    assert e.severity == severity
    assert isinstance(e.message, str)
    assert len(e.message) > 0
    assert isinstance(e.description, str)
    assert len(e.description) > 0


def test_ec001():
    e = EC001("Moter_Run")
    assert e.name == "Moter_Run"
    assert_error_common(e, "EC001", "error")
    assert "Moter_Run" in e.message


def test_ec002():
    e = EC002("TIMER", "DINT")
    assert e.expected == "TIMER"
    assert e.actual == "DINT"
    assert_error_common(e, "EC002", "error")
    assert "TIMER" in e.message
    assert "DINT" in e.message


def test_ec003():
    e = EC003("My_AOI")
    assert e.name == "My_AOI"
    assert_error_common(e, "EC003", "error")


def test_ec004():
    e = EC004("NoSuchRoutine")
    assert e.routine == "NoSuchRoutine"
    assert_error_common(e, "EC004", "error")


def test_ec005():
    e = EC005("Tag", "NonExistent")
    assert e.path == "Tag"
    assert e.member == "NonExistent"
    assert_error_common(e, "EC005", "error")


def test_ec006():
    e = EC006("Arr", 10, 5)
    assert e.name == "Arr"
    assert e.index == 10
    assert e.size == 5
    assert_error_common(e, "EC006", "error")
    assert "10" in e.message


def test_ec007():
    e = EC007("MyTag", "controller")
    assert e.scope == "controller"
    assert_error_common(e, "EC007", "error")


def test_ec008():
    e = EC008(["AOI_A", "AOI_B", "AOI_A"])
    assert len(e.chain) == 3
    assert_error_common(e, "EC008", "error")
    assert "AOI_A -> AOI_B -> AOI_A" in e.message


def test_er009():
    e = ER009("XIC", 1, 0)
    assert e.opcode == "XIC"
    assert e.expected == 1
    assert e.actual == 0
    assert_error_common(e, "ER009", "error")


def test_ec010():
    e = EC010("ProgTag", "ProgB", "ProgA")
    assert e.accessed_from == "ProgB"
    assert_error_common(e, "EC010", "error")


def test_wc001():
    e = WC001("UnusedTag")
    assert e.name == "UnusedTag"
    assert_error_common(e, "WC001", "warning")


def test_wr002():
    e = WR002(3)
    assert e.rung == 3
    assert_error_common(e, "WR002", "warning")


def test_wr003():
    e = WR003("OutputTag")
    assert e.name == "OutputTag"
    assert_error_common(e, "WR003", "warning")


def test_wr004():
    e = WR004("Timer1")
    assert e.name == "Timer1"
    assert_error_common(e, "WR004", "warning")


def test_wc005():
    e = WC005("ProgTag", "CtrlTag")
    assert e.hidden_by == "CtrlTag"
    assert_error_common(e, "WC005", "warning")


def test_ec011():
    e = EC011("TON")
    assert e.name == "TON"
    assert_error_common(e, "EC011", "error")


def test_ec012():
    e = EC012("Arr", 10, 3)
    assert e.name == "Arr"
    assert e.expected == 10
    assert e.actual == 3
    assert_error_common(e, "EC012", "error")


def test_ws101():
    e = WS101("x = 0.1")
    assert e.text == "x = 0.1"
    assert_error_common(e, "WS101", "warning")


def test_ws102():
    e = WS102("x / 0")
    assert e.text == "x / 0"
    assert_error_common(e, "WS102", "warning")


def test_wc103():
    e = WC103(20, 15)
    assert e.complexity == 20
    assert e.threshold == 15
    assert_error_common(e, "WC103", "warning")
    assert "20" in e.message


def test_ws104():
    e = WS104("IF", "DINT")
    assert e.construct == "IF"
    assert e.actual == "DINT"
    assert_error_common(e, "WS104", "warning")


def test_ws105():
    e = WS105("narrow", "LINT", "DINT")
    assert e.name == "narrow"
    assert e.from_type == "LINT"
    assert e.to_type == "DINT"
    assert_error_common(e, "WS105", "warning")


def test_wc106():
    e = WC106("MyUnusedAOI")
    assert e.name == "MyUnusedAOI"
    assert_error_common(e, "WC106", "warning")


def test_ws107():
    e = WS107("IF")
    assert e.construct == "IF"
    assert_error_common(e, "WS107", "warning")


def test_isinstance_union():
    assert isinstance(EC001("x"), LintError)
    assert isinstance(EC002("a", "b"), LintError)
    assert isinstance(WC001("x"), LintError)
    assert isinstance(WC005("x", "y"), LintError)
    assert isinstance(EC011("TON"), LintError)
    assert isinstance(WS101("x = 0.1"), LintError)
    assert isinstance(WC103(20), LintError)
    assert isinstance(WS107("IF"), LintError)
