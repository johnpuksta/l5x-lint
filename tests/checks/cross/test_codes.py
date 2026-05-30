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
    ER009,
    WC001,
    WC005,
    WR002,
    WR003,
    WR004,
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


def test_isinstance_union():
    assert isinstance(EC001("x"), LintError)
    assert isinstance(EC002("a", "b"), LintError)
    assert isinstance(WC001("x"), LintError)
    assert isinstance(WC005("x", "y"), LintError)
