from application import analyze
from domain.checks.rll.wr004_timer_pre import wr004_timer_pre
from domain.models import Controller, Location, Routine, Tag
from domain.rll_models import Instruction, Operand, ParsedRung
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


def test_ton_timer_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("TON", "MyTimer"))])
    c = Controller(name="Test", tags=[Tag(name="MyTimer", data_type="TIMER")])
    table = build_symbol_table(c)
    result = wr004_timer_pre(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WR004"


def test_tof_timer():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("TOF", "MyTimer"))])
    c = Controller(name="Test", tags=[Tag(name="MyTimer", data_type="TIMER")])
    table = build_symbol_table(c)
    result = wr004_timer_pre(r, table, _loc())
    assert len(result) == 1


def test_rto_timer():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("RTO", "MyTimer"))])
    c = Controller(name="Test", tags=[Tag(name="MyTimer", data_type="TIMER")])
    table = build_symbol_table(c)
    result = wr004_timer_pre(r, table, _loc())
    assert len(result) == 1


def test_non_timer_tag_skipped():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("TON", "MyDint"))])
    c = Controller(name="Test", tags=[Tag(name="MyDint", data_type="DINT")])
    table = build_symbol_table(c)
    result = wr004_timer_pre(r, table, _loc())
    assert result == []


def test_non_rll_ignored():
    r = Routine(name="Main", type="ST")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wr004_timer_pre(r, table, _loc())
    assert result == []


def test_xic_not_flagged():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "MyTimer"))])
    c = Controller(name="Test", tags=[Tag(name="MyTimer", data_type="TIMER")])
    table = build_symbol_table(c)
    result = wr004_timer_pre(r, table, _loc())
    assert result == []
