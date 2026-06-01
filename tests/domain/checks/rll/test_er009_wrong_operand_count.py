from domain.checks.rll.er009_wrong_operand_count import er009_wrong_operand_count
from domain.models import Controller, Location, Routine
from domain.rll_models import Instruction, Operand, ParsedRung
from application import analyze
from domain.symbols import build_symbol_table


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


def test_xic_one_operand_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "TagA"))])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = er009_wrong_operand_count(r, table, _loc())
    assert result == []


def test_xic_zero_operands_emits_er009():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC"))])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = er009_wrong_operand_count(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "ER009"


def test_xic_two_operands_emits_er009():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "A", "B"))])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = er009_wrong_operand_count(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "ER009"


def test_mov_two_operands_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("MOV", "Dest", "Src"))])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = er009_wrong_operand_count(r, table, _loc())
    assert result == []


def test_unknown_opcode_skipped():
    r = Routine(
        name="Main", type="RLL", rll_rungs=[_rung(_inst("CUSTOM", "A", "B", "C"))]
    )  # noqa: E501
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = er009_wrong_operand_count(r, table, _loc())
    assert result == []


def test_non_rll_ignored():
    r = Routine(name="Main", type="ST")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = er009_wrong_operand_count(r, table, _loc())
    assert result == []


def test_afi_zero_operands_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(Instruction(opcode="AFI"))])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = er009_wrong_operand_count(r, table, _loc())
    assert result == []
