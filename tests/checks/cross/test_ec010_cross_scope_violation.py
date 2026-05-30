from l5x_lint.checks.cross.ec010_cross_scope_violation import (
    ec010_cross_scope_violation,
)
from l5x_lint.domain.models import Controller, Location, Program, Routine, Tag
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


def test_same_program_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "LocalTag"))])
    c = Controller(name="Test", programs=[
        Program(name="Prog", tags=[Tag(name="LocalTag", data_type="DINT")]),
    ])
    table = build_symbol_table(c)
    result = ec010_cross_scope_violation(r, table, _loc(program="Prog"))
    assert result == []


def test_controller_tag_cross_program_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "CtrlTag"))])
    c = Controller(name="Test",
                   tags=[Tag(name="CtrlTag", data_type="DINT")],
                   programs=[Program(name="ProgA"), Program(name="ProgB")])
    table = build_symbol_table(c)
    result = ec010_cross_scope_violation(r, table, _loc(program="ProgA"))
    assert result == []


def test_different_program_tag_emits_ec010():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "PrivateTag"))])
    c = Controller(name="Test", programs=[
        Program(name="ProgA"),
        Program(name="ProgB", tags=[Tag(name="PrivateTag", data_type="DINT")]),
    ])
    table = build_symbol_table(c)
    loc = _loc(program="ProgA")
    result = ec010_cross_scope_violation(r, table, loc)
    assert len(result) == 1
    assert result[0].code == "EC010"


def test_non_rll_ignored():
    r = Routine(name="Main", type="FBD")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec010_cross_scope_violation(r, table, _loc())
    assert result == []
