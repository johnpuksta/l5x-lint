from l5x_lint.checks.rll.er016_fal_incomplete import er016_fal_incomplete
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.pipeline.symbols import SymbolTable


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_fal_complete_operands_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1,
                [
                    Instruction(
                        opcode="FAL",
                        operands=[
                            Operand(value="INC"),
                            Operand(value="MyCtrl"),
                            Operand(value="MyDest"),
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = er016_fal_incomplete(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_fal_zero_operands_emits_er016():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(2, [Instruction(opcode="FAL", operands=[])]),
        ],
    )
    diags = er016_fal_incomplete(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "ER016"
    assert "FAL" in diags[0].message
    assert diags[0].location.rung == 2


def test_fsc_one_operand_emits_er016():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                3,
                [
                    Instruction(opcode="FSC", operands=[Operand(value="ALL")]),
                ],
            ),
        ],
    )
    diags = er016_fal_incomplete(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "ER016"
    assert "FSC" in diags[0].message


def test_fsc_two_operands_emits_er016():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                4,
                [
                    Instruction(
                        opcode="FSC",
                        operands=[
                            Operand(value="ALL"),
                            Operand(value="MyCtrl"),
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = er016_fal_incomplete(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1


def test_non_fal_fsc_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(1, [Instruction(opcode="XIC", operands=[Operand(value="A")])]),
        ],
    )
    diags = er016_fal_incomplete(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_non_rll_ignored():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = er016_fal_incomplete(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_fal_in_branch():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                5,
                [
                    Instruction(
                        opcode="XIC",
                        operands=[],
                        branch=[
                            [Instruction(opcode="FAL", operands=[])],
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = er016_fal_incomplete(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1


def test_fal_enough_operands_in_branch_no_diag():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                6,
                [
                    Instruction(
                        opcode="XIC",
                        operands=[],
                        branch=[
                            [
                                Instruction(
                                    opcode="FAL",
                                    operands=[
                                        Operand("ALL"),
                                        Operand("Ctrl"),
                                        Operand("Dest"),
                                    ],
                                )
                            ],
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = er016_fal_incomplete(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []
