from domain.checks.rll.wr007_inputs_no_output import wr007_inputs_no_output
from domain.models import Location, Routine
from domain.rll_models import Instruction, Operand, ParsedRung
from domain.symbols import SymbolTable


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_input_and_output_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1,
                [
                    Instruction(opcode="XIC", operands=[Operand(value="A")]),
                    Instruction(opcode="OTE", operands=[Operand(value="B")]),
                ],
            ),
        ],
    )
    diags = wr007_inputs_no_output(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_inputs_only_emits_wr007():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1,
                [
                    Instruction(opcode="XIC", operands=[Operand(value="A")]),
                    Instruction(opcode="XIO", operands=[Operand(value="B")]),
                ],
            ),
        ],
    )
    diags = wr007_inputs_no_output(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "WR007"


def test_no_inputs_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(1, [Instruction(opcode="OTE", operands=[Operand(value="B")])]),
        ],
    )
    diags = wr007_inputs_no_output(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_non_rll_ignored():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = wr007_inputs_no_output(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_rung_with_ton_output_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1,
                [
                    Instruction(opcode="XIC", operands=[Operand(value="A")]),
                    Instruction(opcode="TON", operands=[Operand(value="T")]),
                ],
            ),
        ],
    )
    diags = wr007_inputs_no_output(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []
