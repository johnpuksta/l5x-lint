from l5x_lint.domain.checks.rll.er013_invalid_jmp_target import er013_invalid_jmp_target
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.domain.symbols import SymbolTable


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_jmp_to_existing_label_no_diagnostic():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1, [Instruction(opcode="LBL", operands=[Operand(value="Mark")])]
            ),
            _make_rung(
                2, [Instruction(opcode="JMP", operands=[Operand(value="Mark")])]
            ),
        ],
    )
    diags = er013_invalid_jmp_target(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_jmp_to_nonexistent_label_emits_er013():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1, [Instruction(opcode="JMP", operands=[Operand(value="GoneLabel")])]
            ),
        ],
    )
    diags = er013_invalid_jmp_target(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "ER013"
    assert "GoneLabel" in diags[0].message


def test_case_insensitive_label_match():
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1, [Instruction(opcode="LBL", operands=[Operand(value="MARK")])]
            ),
            _make_rung(
                2, [Instruction(opcode="JMP", operands=[Operand(value="mark")])]
            ),
        ],
    )
    diags = er013_invalid_jmp_target(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_non_rll_ignored():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = er013_invalid_jmp_target(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_jmp_label_in_branch():
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
                        branch=[
                            [
                                Instruction(
                                    opcode="JMP", operands=[Operand(value="Missing")]
                                )
                            ]
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = er013_invalid_jmp_target(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "ER013"
