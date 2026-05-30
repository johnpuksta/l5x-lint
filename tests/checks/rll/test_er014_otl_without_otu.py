from l5x_lint.checks.rll.er014_otl_without_otu import er014_otl_without_otu
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.pipeline.symbols import SymbolTable


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_otl_with_otu_no_diagnostic():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(1, [Instruction(opcode="OTL", operands=[Operand(value="MyBit")])]),
        _make_rung(2, [Instruction(opcode="OTU", operands=[Operand(value="MyBit")])]),
    ])
    diags = er014_otl_without_otu(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_otl_without_otu_emits_er014():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(1, [Instruction(opcode="OTL", operands=[Operand(value="MyBit")])]),
    ])
    diags = er014_otl_without_otu(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "ER014"
    assert "MyBit" in diags[0].message


def test_multiple_otls_same_tag():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(1, [Instruction(opcode="OTL", operands=[Operand(value="BitA")])]),
        _make_rung(2, [Instruction(opcode="OTL", operands=[Operand(value="BitA")])]),
        _make_rung(3, [Instruction(opcode="OTU", operands=[Operand(value="BitA")])]),
    ])
    diags = er014_otl_without_otu(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_otl_and_otu_different_tags():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(1, [Instruction(opcode="OTL", operands=[Operand(value="BitA")])]),
        _make_rung(2, [Instruction(opcode="OTU", operands=[Operand(value="BitB")])]),
    ])
    diags = er014_otl_without_otu(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "ER014"


def test_no_latch_ops_no_diagnostic():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(1, [Instruction(opcode="XIC", operands=[Operand(value="A")])]),
    ])
    diags = er014_otl_without_otu(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_non_rll_ignored():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = er014_otl_without_otu(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []
