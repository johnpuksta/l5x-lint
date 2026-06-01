from domain.checks.rll.wr005_nop_present import wr005_nop_present
from domain.models import Location, Routine
from domain.rll_models import Instruction, Operand, ParsedRung
from domain.symbols import SymbolTable


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_nop_present_emits_wr005():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(3, [Instruction(opcode="NOP", operands=[])]),
        ],
    )
    diags = wr005_nop_present(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "WR005"
    assert diags[0].location.rung == 3


def test_no_nop_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(1, [Instruction(opcode="XIC", operands=[Operand(value="A")])]),
        ],
    )
    diags = wr005_nop_present(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_non_rll_ignored():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = wr005_nop_present(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_nop_in_branch():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1,
                [
                    Instruction(
                        opcode="XIC",
                        operands=[Operand(value="A")],
                        branch=[[Instruction(opcode="NOP", operands=[])]],
                    ),
                ],
            ),
        ],
    )
    diags = wr005_nop_present(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
