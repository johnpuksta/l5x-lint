from l5x_lint.checks.rll.wr008_cop_overlap import wr008_cop_overlap
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.pipeline.symbols import SymbolTable


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_cop_different_tags_no_diagnostic():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(1, [
            Instruction(opcode="COP", operands=[
                Operand(value="SourceTag"), Operand(value="DestTag"),
                Operand(value="10"),
            ]),
        ]),
    ])
    diags = wr008_cop_overlap(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_cop_same_base_tag_emits_wr008():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(2, [
            Instruction(opcode="COP", operands=[
                Operand(value="MyArr[0]"), Operand(value="MyArr[1]"),
                Operand(value="10"),
            ]),
        ]),
    ])
    diags = wr008_cop_overlap(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "WR008"
    assert diags[0].location.rung == 2


def test_cps_same_tag_emits_wr008():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(3, [
            Instruction(opcode="CPS", operands=[
                Operand(value="Data"), Operand(value="Data"),
                Operand(value="5"),
            ]),
        ]),
    ])
    diags = wr008_cop_overlap(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1


def test_cop_same_tag_exact_match():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(4, [
            Instruction(opcode="COP", operands=[
                Operand(value="MyStruct.FieldA"), Operand(value="MyStruct.FieldA"),
                Operand(value="1"),
            ]),
        ]),
    ])
    diags = wr008_cop_overlap(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1


def test_cop_different_members_no_diagnostic():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(5, [
            Instruction(opcode="COP", operands=[
                Operand(value="MyStruct.FieldA"), Operand(value="MyStruct.FieldB"),
                Operand(value="1"),
            ]),
        ]),
    ])
    diags = wr008_cop_overlap(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_cop_not_enough_operands_no_diagnostic():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(6, [Instruction(opcode="COP", operands=[])]),
    ])
    diags = wr008_cop_overlap(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_non_cop_no_diagnostic():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(1, [Instruction(opcode="XIC", operands=[Operand(value="A")])]),
    ])
    diags = wr008_cop_overlap(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_non_rll_ignored():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = wr008_cop_overlap(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_cop_in_branch():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(7, [
            Instruction(opcode="XIC", operands=[], branch=[
                [Instruction(
                    opcode="COP",
                    operands=[Operand("A"), Operand("A"), Operand("5")],
                )],
            ]),
        ]),
    ])
    diags = wr008_cop_overlap(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
