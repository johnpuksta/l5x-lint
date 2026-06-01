from l5x_lint.checks.rll.er015_mcr_zone import er015_mcr_zone
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.rll_models import Instruction, ParsedRung
from l5x_lint.domain.symbols import SymbolTable


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_paired_mcrs_no_diagnostic():
    r = Routine(
        name="Prog",
        type="RLL",
        rll_rungs=[
            _make_rung(0, [Instruction(opcode="MCR", operands=[])]),
            _make_rung(1, [Instruction(opcode="MCR", operands=[])]),
        ],
    )
    diags = er015_mcr_zone(r, SymbolTable(), Location(program="P", routine="Prog"))
    assert diags == []


def test_single_mcr_emits_er015():
    r = Routine(
        name="Prog",
        type="RLL",
        rll_rungs=[
            _make_rung(0, [Instruction(opcode="MCR", operands=[])]),
        ],
    )
    diags = er015_mcr_zone(r, SymbolTable(), Location(program="P", routine="Prog"))
    assert len(diags) == 1
    assert diags[0].code == "ER015"
    assert "Prog" in diags[0].message


def test_three_mcrs_unpaired():
    r = Routine(
        name="Prog",
        type="RLL",
        rll_rungs=[
            _make_rung(0, [Instruction(opcode="MCR", operands=[])]),
            _make_rung(1, [Instruction(opcode="XIC", operands=[])]),
            _make_rung(2, [Instruction(opcode="MCR", operands=[])]),
            _make_rung(3, [Instruction(opcode="MCR", operands=[])]),
        ],
    )
    diags = er015_mcr_zone(r, SymbolTable(), Location(program="P", routine="Prog"))
    assert len(diags) == 1


def test_no_mcr_no_diagnostic():
    r = Routine(
        name="Prog",
        type="RLL",
        rll_rungs=[
            _make_rung(0, [Instruction(opcode="XIC", operands=[])]),
        ],
    )
    diags = er015_mcr_zone(r, SymbolTable(), Location(program="P", routine="Prog"))
    assert diags == []


def test_non_rll_ignored():
    r = Routine(name="Prog", type="ST", st_body=None)
    diags = er015_mcr_zone(r, SymbolTable(), Location(program="P", routine="Prog"))
    assert diags == []


def test_mcr_in_branch_counted():
    r = Routine(
        name="Prog",
        type="RLL",
        rll_rungs=[
            _make_rung(
                0,
                [
                    Instruction(
                        opcode="XIC",
                        operands=[],
                        branch=[
                            [Instruction(opcode="MCR", operands=[])],
                        ],
                    ),
                ],
            ),
        ],
    )
    diags = er015_mcr_zone(r, SymbolTable(), Location(program="P", routine="Prog"))
    assert len(diags) == 1


def test_empty_rungs_no_diagnostic():
    r = Routine(name="Prog", type="RLL", rll_rungs=[])
    diags = er015_mcr_zone(r, SymbolTable(), Location(program="P", routine="Prog"))
    assert diags == []
