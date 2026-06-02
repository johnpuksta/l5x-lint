from application import analyze
from domain.checks.cross.ec006_array_bounds import ec006_array_bounds
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


def test_valid_array_index_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("MOV", "MyArr[0]"))])
    c = Controller(
        name="Test", tags=[Tag(name="MyArr", data_type="DINT", dimensions=(10,))]
    )  # noqa: E501
    table = build_symbol_table(c)
    result = ec006_array_bounds(r, table, _loc())
    assert result == []


def test_oor_array_index_emits_ec006():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("MOV", "MyArr[10]"))])
    c = Controller(
        name="Test", tags=[Tag(name="MyArr", data_type="DINT", dimensions=(10,))]
    )  # noqa: E501
    table = build_symbol_table(c)
    result = ec006_array_bounds(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC006"


def test_unknown_tag_skipped():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("MOV", "NoTag[0]"))])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec006_array_bounds(r, table, _loc())
    assert result == []


def test_non_array_tag_skipped():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("MOV", "MyTag[0]"))])
    c = Controller(name="Test", tags=[Tag(name="MyTag", data_type="DINT")])
    table = build_symbol_table(c)
    result = ec006_array_bounds(r, table, _loc())
    assert result == []


def test_empty_routine():
    r = Routine(name="Main", type="RLL", rll_rungs=[])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec006_array_bounds(r, table, _loc())
    assert result == []


def test_member_with_array():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("MOV", "MyArr[5]"))])
    c = Controller(
        name="Test", tags=[Tag(name="MyArr", data_type="MyUDT", dimensions=(6,))]
    )  # noqa: E501
    table = build_symbol_table(c)
    result = ec006_array_bounds(r, table, _loc())
    assert result == []


def test_negative_index_not_flagged():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("MOV", "Arr[-1]"))])
    c = Controller(
        name="Test", tags=[Tag(name="Arr", data_type="DINT", dimensions=(10,))]
    )  # noqa: E501
    table = build_symbol_table(c)
    result = ec006_array_bounds(r, table, _loc())
    assert result == []
