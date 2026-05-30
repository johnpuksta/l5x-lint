from l5x_lint.checks.rll.wr006_sus_production import wr006_sus_production
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.pipeline.symbols import SymbolTable


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_sus_present_emits_wr006():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(2, [Instruction(opcode="SUS", operands=[Operand(value="Debug")])]),
    ])
    diags = wr006_sus_production(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "WR006"


def test_no_sus_no_diagnostic():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        _make_rung(1, [Instruction(opcode="XIC", operands=[Operand(value="A")])]),
    ])
    diags = wr006_sus_production(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_non_rll_ignored():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = wr006_sus_production(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []
