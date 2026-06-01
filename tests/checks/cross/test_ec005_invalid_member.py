from l5x_lint.checks.cross.ec005_invalid_member import ec005_invalid_member
from l5x_lint.domain.models import (
    Controller,
    DataType,
    Location,
    Member,
    Routine,
    Tag,
)
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


def test_valid_member_no_diagnostic():
    dt = DataType(
        name="MyUDT",
        family="NoFamily",
        class_="",
        members=[Member(name="Field1", data_type="DINT")],
    )
    r = Routine(
        name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "MyTag.Field1"))]
    )  # noqa: E501
    c = Controller(
        name="Test", tags=[Tag(name="MyTag", data_type="MyUDT")], data_types=[dt]
    )
    table = build_symbol_table(c)
    result = ec005_invalid_member(r, table, _loc())
    assert result == []


def test_invalid_member_emits_ec005():
    dt = DataType(
        name="MyUDT",
        family="NoFamily",
        class_="",
        members=[Member(name="Field1", data_type="DINT")],
    )
    r = Routine(
        name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "MyTag.NoSuch"))]
    )  # noqa: E501
    c = Controller(
        name="Test", tags=[Tag(name="MyTag", data_type="MyUDT")], data_types=[dt]
    )
    table = build_symbol_table(c)
    result = ec005_invalid_member(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC005"


def test_unknown_tag_skipped():
    r = Routine(
        name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "NoTag.Field1"))]
    )  # noqa: E501
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec005_invalid_member(r, table, _loc())
    assert result == []


def test_no_members_on_type_skipped():
    r = Routine(
        name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "MyTag.Field1"))]
    )  # noqa: E501
    c = Controller(name="Test", tags=[Tag(name="MyTag", data_type="DINT")])
    table = build_symbol_table(c)
    result = ec005_invalid_member(r, table, _loc())
    assert result == []


def test_non_rll_ignored():
    r = Routine(name="Main", type="FBD")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec005_invalid_member(r, table, _loc())
    assert result == []
