from l5x_lint.checks.rll.wr009_gsv_invalid_class import wr009_gsv_invalid_class
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.pipeline.symbols import SymbolTable


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_gsv_known_class_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1,
                [
                    Instruction(
                        opcode="GSV",
                        operands=[
                            Operand(value="Program"),
                            Operand(value="MyProg"),
                            Operand(value="Name"),
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = wr009_gsv_invalid_class(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_gsv_invalid_class_emits_wr009():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                2,
                [
                    Instruction(
                        opcode="GSV",
                        operands=[
                            Operand(value="InvalidClass"),
                            Operand(value="Obj"),
                            Operand(value="Attr"),
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = wr009_gsv_invalid_class(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "WR009"
    assert "InvalidClass" in diags[0].message
    assert diags[0].location.rung == 2


def test_ssv_invalid_class_emits_wr009():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                3,
                [
                    Instruction(
                        opcode="SSV",
                        operands=[
                            Operand(value="FooBar"),
                            Operand(value="Obj"),
                            Operand(value="Attr"),
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = wr009_gsv_invalid_class(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1


def test_gsv_controller_class_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1,
                [
                    Instruction(
                        opcode="GSV",
                        operands=[
                            Operand(value="Controller"),
                            Operand(value=""),
                            Operand(value="Name"),
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = wr009_gsv_invalid_class(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_gsv_module_class_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1,
                [
                    Instruction(
                        opcode="GSV",
                        operands=[
                            Operand(value="Module"),
                            Operand(value="Local"),
                            Operand(value="EntryStatus"),
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = wr009_gsv_invalid_class(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_non_gsv_ssv_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(1, [Instruction(opcode="XIC", operands=[Operand(value="A")])]),
        ],
    )
    diags = wr009_gsv_invalid_class(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_non_rll_ignored():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = wr009_gsv_invalid_class(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_gsv_zero_operands_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(1, [Instruction(opcode="GSV", operands=[])]),
        ],
    )
    diags = wr009_gsv_invalid_class(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_gsv_in_branch():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                4,
                [
                    Instruction(
                        opcode="XIC",
                        operands=[],
                        branch=[
                            [
                                Instruction(
                                    opcode="GSV",
                                    operands=[
                                        Operand("BadClass"),
                                        Operand("O"),
                                        Operand("A"),
                                    ],
                                )
                            ],
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = wr009_gsv_invalid_class(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
