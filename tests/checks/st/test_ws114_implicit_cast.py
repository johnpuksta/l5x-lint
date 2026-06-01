from l5x_lint.checks.st.ws114_implicit_cast import ws114_implicit_cast
from l5x_lint.domain.models import Location, Routine, TagPath, TagPathSegment
from l5x_lint.domain.st_models import StAssignment, StBinaryOp, StLiteral, StProgram
from l5x_lint.pipeline.symbols import SymbolTable


def _make_routine(stmts) -> Routine:
    return Routine(name="Test", type="ST", st_body=StProgram(statements=stmts))


def _tp(name: str) -> TagPath:
    return TagPath(segments=[TagPathSegment(name=name)])


def test_int_int_no_diagnostic():
    r = _make_routine(
        [
            StAssignment(
                target=_tp("x"),
                expression=StBinaryOp(
                    left=StLiteral(value=1),
                    op="+",
                    right=StLiteral(value=2),
                ),
                line=1,
            ),
        ]
    )
    diags = ws114_implicit_cast(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_float_float_no_diagnostic():
    r = _make_routine(
        [
            StAssignment(
                target=_tp("x"),
                expression=StBinaryOp(
                    left=StLiteral(value=1.0),
                    op="+",
                    right=StLiteral(value=2.0),
                ),
                line=1,
            ),
        ]
    )
    diags = ws114_implicit_cast(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_int_float_emits_ws114():
    r = _make_routine(
        [
            StAssignment(
                target=_tp("x"),
                expression=StBinaryOp(
                    left=StLiteral(value=1),
                    op="+",
                    right=StLiteral(value=2.5),
                ),
                line=5,
            ),
        ]
    )
    diags = ws114_implicit_cast(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "WS114"
    assert "INT" in diags[0].message
    assert "REAL" in diags[0].message


def test_float_int_emits_ws114():
    r = _make_routine(
        [
            StAssignment(
                target=_tp("x"),
                expression=StBinaryOp(
                    left=StLiteral(value=3.14),
                    op="*",
                    right=StLiteral(value=2),
                ),
                line=10,
            ),
        ]
    )
    diags = ws114_implicit_cast(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ws114_implicit_cast(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []
