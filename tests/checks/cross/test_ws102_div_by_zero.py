from l5x_lint.checks.cross.ws102_div_by_zero import ws102_div_by_zero
from l5x_lint.domain.models import Controller, Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.pipeline.symbols import build_symbol_table


def _loc(program="", routine=""):
    return Location(program=program, routine=routine)


def test_st_division_by_literal_zero():
    r = Routine(name="Main", type="ST", cdata="result := x / 0;")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws102_div_by_zero(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WS102"


def test_st_mod_by_literal_zero():
    r = Routine(name="Main", type="ST", cdata="result := x MOD 0;")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws102_div_by_zero(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WS102"


def test_st_variable_divisor_no_diagnostic():
    r = Routine(name="Main", type="ST", cdata="result := x / y;")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws102_div_by_zero(r, table, _loc())
    assert result == []


def test_rll_cpt_with_div_by_zero():
    r = Routine(
        name="Main", type="RLL",
        rll_rungs=[ParsedRung(
            number=0, text="",
            instructions=[Instruction(opcode="CPT", operands=[Operand(value="Dest"), Operand(value="A / 0")])],
        )],
    )
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws102_div_by_zero(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WS102"


def test_empty_text():
    r = Routine(name="Main", type="ST", cdata="")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws102_div_by_zero(r, table, _loc())
    assert result == []
