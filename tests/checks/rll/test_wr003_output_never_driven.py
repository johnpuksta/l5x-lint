from l5x_lint.checks.rll.wr003_output_never_driven import wr003_output_never_driven
from l5x_lint.domain.models import Controller, Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.pipeline import analyze
from l5x_lint.pipeline.symbols import build_symbol_table


def _reset_registry():
    analyze._registry.clear()


def _loc(program="Prog", routine="Main", rung=None):
    return Location(program=program, routine=routine, rung=rung)


def _rung(*instructions):
    return ParsedRung(number=0, text="", instructions=list(instructions))


def _inst(opcode, *operand_values):
    return Instruction(
        opcode=opcode, operands=[Operand(value=v) for v in operand_values]
    )


def test_input_and_output_no_diagnostic():
    rungs = [
        ParsedRung(number=0, text="", instructions=[_inst("XIC", "MyTag")]),
        ParsedRung(number=1, text="", instructions=[_inst("OTE", "MyTag")]),
    ]
    r = Routine(name="Main", type="RLL", rll_rungs=rungs)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wr003_output_never_driven(r, table, _loc())
    assert result == []


def test_input_only_emits_wr003():
    rungs = [ParsedRung(number=0, text="", instructions=[_inst("XIC", "InputOnly")])]
    r = Routine(name="Main", type="RLL", rll_rungs=rungs)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wr003_output_never_driven(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WR003"


def test_output_only_no_diagnostic():
    rungs = [ParsedRung(number=0, text="", instructions=[_inst("OTE", "MyTag")])]
    r = Routine(name="Main", type="RLL", rll_rungs=rungs)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wr003_output_never_driven(r, table, _loc())
    assert result == []


def test_non_rll_ignored():
    r = Routine(name="Main", type="ST")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wr003_output_never_driven(r, table, _loc())
    assert result == []


def test_jsr_params_not_considered():
    jsr = Instruction(
        opcode="JSR",
        operands=[Operand(value="Sub"), Operand(value="ShouldNotBeInput")],
    )
    rungs = [ParsedRung(number=0, text="", instructions=[jsr])]
    r = Routine(name="Main", type="RLL", rll_rungs=rungs)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wr003_output_never_driven(r, table, _loc())
    assert result == []


def test_empty_routine():
    r = Routine(name="Main", type="RLL", rll_rungs=[])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wr003_output_never_driven(r, table, _loc())
    assert result == []
