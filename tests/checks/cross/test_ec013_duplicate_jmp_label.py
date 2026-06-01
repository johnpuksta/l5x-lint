import importlib

from l5x_lint.checks.cross import ec013_duplicate_jmp_label
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.domain.symbols import SymbolTable


def _reset():
    importlib.reload(ec013_duplicate_jmp_label)


def _make_rung(num: int, instructions: list[Instruction]) -> ParsedRung:
    return ParsedRung(number=num, text="", instructions=instructions)


def test_unique_labels_no_diagnostic():
    _reset()
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1, [Instruction(opcode="LBL", operands=[Operand(value="Start")])]
            ),
            _make_rung(2, [Instruction(opcode="LBL", operands=[Operand(value="End")])]),
        ],
    )
    diags = ec013_duplicate_jmp_label.ec013_duplicate_jmp_label(
        r,
        SymbolTable(),
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_duplicate_label_emits_ec013():
    _reset()
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1, [Instruction(opcode="LBL", operands=[Operand(value="Mark")])]
            ),
            _make_rung(
                2, [Instruction(opcode="LBL", operands=[Operand(value="Mark")])]
            ),
        ],
    )
    diags = ec013_duplicate_jmp_label.ec013_duplicate_jmp_label(
        r,
        SymbolTable(),
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
    assert diags[0].code == "EC013"


def test_no_duplicate_reports():
    _reset()
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(1, [Instruction(opcode="LBL", operands=[Operand(value="X")])]),
            _make_rung(2, [Instruction(opcode="LBL", operands=[Operand(value="X")])]),
            _make_rung(3, [Instruction(opcode="LBL", operands=[Operand(value="X")])]),
        ],
    )
    diags = ec013_duplicate_jmp_label.ec013_duplicate_jmp_label(
        r,
        SymbolTable(),
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1


def test_non_rll_ignored():
    _reset()
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec013_duplicate_jmp_label.ec013_duplicate_jmp_label(
        r,
        SymbolTable(),
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_case_insensitive_duplicate():
    _reset()
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            _make_rung(
                1, [Instruction(opcode="LBL", operands=[Operand(value="MARK")])]
            ),
            _make_rung(
                2, [Instruction(opcode="LBL", operands=[Operand(value="mark")])]
            ),
        ],
    )
    diags = ec013_duplicate_jmp_label.ec013_duplicate_jmp_label(
        r,
        SymbolTable(),
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
