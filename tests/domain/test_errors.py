from l5x_lint.domain.errors import (
    E001,
    E002,
    E003,
    E004,
    E005,
    E006,
    E007,
    E008,
    E009,
    E010,
    W001,
    W002,
    W003,
    W004,
    W005,
    LintError,
)


def assert_error_common(e, code, severity):
    assert e.code == code
    assert e.severity == severity
    assert isinstance(e.message, str)
    assert len(e.message) > 0
    assert isinstance(e.description, str)
    assert len(e.description) > 0


def test_e001():
    e = E001("Moter_Run")
    assert e.name == "Moter_Run"
    assert_error_common(e, "E001", "error")
    assert "Moter_Run" in e.message


def test_e002():
    e = E002("TIMER", "DINT")
    assert e.expected == "TIMER"
    assert e.actual == "DINT"
    assert_error_common(e, "E002", "error")
    assert "TIMER" in e.message
    assert "DINT" in e.message


def test_e003():
    e = E003("My_AOI")
    assert e.name == "My_AOI"
    assert_error_common(e, "E003", "error")


def test_e004():
    e = E004("NoSuchRoutine")
    assert e.routine == "NoSuchRoutine"
    assert_error_common(e, "E004", "error")


def test_e005():
    e = E005("Tag", "NonExistent")
    assert e.path == "Tag"
    assert e.member == "NonExistent"
    assert_error_common(e, "E005", "error")


def test_e006():
    e = E006("Arr", 10, 5)
    assert e.name == "Arr"
    assert e.index == 10
    assert e.size == 5
    assert_error_common(e, "E006", "error")
    assert "10" in e.message


def test_e007():
    e = E007("MyTag", "controller")
    assert e.scope == "controller"
    assert_error_common(e, "E007", "error")


def test_e008():
    e = E008(["AOI_A", "AOI_B", "AOI_A"])
    assert len(e.chain) == 3
    assert_error_common(e, "E008", "error")
    assert "AOI_A -> AOI_B -> AOI_A" in e.message


def test_e009():
    e = E009("XIC", 1, 0)
    assert e.opcode == "XIC"
    assert e.expected == 1
    assert e.actual == 0
    assert_error_common(e, "E009", "error")


def test_e010():
    e = E010("ProgTag", "ProgB", "ProgA")
    assert e.accessed_from == "ProgB"
    assert_error_common(e, "E010", "error")


def test_w001():
    e = W001("UnusedTag")
    assert e.name == "UnusedTag"
    assert_error_common(e, "W001", "warning")


def test_w002():
    e = W002(3)
    assert e.rung == 3
    assert_error_common(e, "W002", "warning")


def test_w003():
    e = W003("OutputTag")
    assert e.name == "OutputTag"
    assert_error_common(e, "W003", "warning")


def test_w004():
    e = W004("Timer1")
    assert e.name == "Timer1"
    assert_error_common(e, "W004", "warning")


def test_w005():
    e = W005("ProgTag", "CtrlTag")
    assert e.hidden_by == "CtrlTag"
    assert_error_common(e, "W005", "warning")


def test_isinstance_union():
    assert isinstance(E001("x"), LintError)
    assert isinstance(E002("a", "b"), LintError)
    assert isinstance(W001("x"), LintError)
    assert isinstance(W005("x", "y"), LintError)
