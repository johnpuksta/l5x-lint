from domain.checks.st.ws111_literal_overflow import ws111_literal_overflow
from domain.models import Location, Routine, TagPath, TagPathSegment
from domain.st_models import (
    StAssignment,
    StBinaryOp,
    StFor,
    StLiteral,
    StProgram,
    StTagRef,
)
from domain.symbols import SymbolTable


def _make_routine(stmts) -> Routine:
    return Routine(name="Test", type="ST", st_body=StProgram(statements=stmts))


def _tp(name: str) -> TagPath:
    return TagPath(segments=[TagPathSegment(name=name)])


def test_small_literal_no_diagnostic():
    r = _make_routine(
        [
            StAssignment(
                target=_tp("x"),
                expression=StLiteral(value=42),
                line=1,
            ),
        ]
    )
    diags = ws111_literal_overflow(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_literal_exceeds_dint_max_emits_ws111():
    r = _make_routine(
        [
            StAssignment(
                target=_tp("x"),
                expression=StLiteral(value=9_999_999_999),
                line=5,
            ),
        ]
    )
    diags = ws111_literal_overflow(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "WS111"
    assert diags[0].location.line == 5


def test_literal_below_dint_min_emits_ws111():
    r = _make_routine(
        [
            StAssignment(
                target=_tp("x"),
                expression=StLiteral(value=-9_999_999_999_999),
                line=10,
            ),
        ]
    )
    diags = ws111_literal_overflow(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1


def test_float_literal_overflow():
    r = _make_routine(
        [
            StAssignment(
                target=_tp("x"),
                expression=StLiteral(value=1e40),
                line=15,
            ),
        ]
    )
    diags = ws111_literal_overflow(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ws111_literal_overflow(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_literal_in_binary_op():
    r = _make_routine(
        [
            StAssignment(
                target=_tp("x"),
                expression=StBinaryOp(
                    left=StLiteral(value=42),
                    op="+",
                    right=StLiteral(value=9_999_999_999),
                ),
                line=20,
            ),
        ]
    )
    diags = ws111_literal_overflow(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1


def test_literal_in_for_bound():
    r = _make_routine(
        [
            StFor(
                variable=_tp("i"),
                start=StLiteral(value=0),
                end=StLiteral(value=9_999_999_999),
                body=[],
                line=25,
            ),
        ]
    )
    diags = ws111_literal_overflow(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
