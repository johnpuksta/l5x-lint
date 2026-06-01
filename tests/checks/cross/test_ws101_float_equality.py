from l5x_lint.checks.cross.ws101_float_equality import ws101_float_equality
from l5x_lint.domain.models import (
    Controller,
    Location,
    Routine,
    TagPath,
    TagPathSegment,
)
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.domain.st_models import (
    StAssignment,
    StBinaryOp,
    StLiteral,
    StProgram,
    StTagRef,
)
from l5x_lint.domain.symbols import build_symbol_table


def _loc(program="", routine=""):
    return Location(program=program, routine=routine)


def test_st_float_equality_emits_ws101():
    prog = StProgram(
        statements=[
            StAssignment(
                target=TagPath(segments=[TagPathSegment(name="flag")]),
                expression=StBinaryOp(
                    left=StBinaryOp(
                        left=StTagRef(
                            path=TagPath(segments=[TagPathSegment(name="r")])
                        ),
                        op="+",
                        right=StLiteral(value=0.2),
                    ),
                    op="=",
                    right=StLiteral(value=0.3),
                ),
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws101_float_equality(r, table, _loc())
    assert len(result) >= 1
    assert result[0].code == "WS101"


def test_st_dint_comparison_no_diagnostic():
    prog = StProgram(
        statements=[
            StAssignment(
                target=TagPath(segments=[TagPathSegment(name="flag")]),
                expression=StBinaryOp(
                    left=StTagRef(path=TagPath(segments=[TagPathSegment(name="x")])),
                    op="=",
                    right=StTagRef(path=TagPath(segments=[TagPathSegment(name="y")])),
                ),
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws101_float_equality(r, table, _loc())
    assert result == []


def test_rll_equ_with_float_emits_ws101():
    r = Routine(
        name="Main",
        type="RLL",
        rll_rungs=[
            ParsedRung(
                number=0,
                text="",
                instructions=[
                    Instruction(
                        opcode="EQU",
                        operands=[Operand(value="Motor_Speed"), Operand(value="100.5")],
                    )
                ],
            )
        ],
    )
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws101_float_equality(r, table, _loc())
    assert len(result) >= 1
    assert result[0].code == "WS101"


def test_rll_grt_no_float_no_diagnostic():
    r = Routine(
        name="Main",
        type="RLL",
        rll_rungs=[
            ParsedRung(
                number=0,
                text="",
                instructions=[
                    Instruction(
                        opcode="GRT",
                        operands=[Operand(value="Speed"), Operand(value="100")],
                    )
                ],
            )
        ],
    )
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws101_float_equality(r, table, _loc())
    assert result == []


def test_empty_text():
    r = Routine(name="Main", type="ST", st_body=StProgram(statements=[]))
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws101_float_equality(r, table, _loc())
    assert result == []
