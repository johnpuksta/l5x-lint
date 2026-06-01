from l5x_lint.checks.st.ws110_dead_code import ws110_dead_code
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import (
    StAssignment,
    StLiteral,
    StProgram,
    StReturn,
    StTagRef,
)
from l5x_lint.domain.models import TagPath, TagPathSegment
from l5x_lint.pipeline.symbols import SymbolTable


def test_return_no_following_statements_no_diagnostic():
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StReturn(line=3),
            ]
        ),
    )
    diags = ws110_dead_code(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_return_with_dead_code_emits_ws110():
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StReturn(line=3),
                StAssignment(
                    target=TagPath(segments=[TagPathSegment(name="x")]),
                    expression=StLiteral(value=5),
                    line=5,
                ),
            ]
        ),
    )
    diags = ws110_dead_code(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "WS110"
    assert "RETURN" in diags[0].message


def test_no_body():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ws110_dead_code(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ws110_dead_code(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_return_in_middle_marks_all_subsequent_as_dead():
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StAssignment(
                    target=TagPath(segments=[TagPathSegment(name="a")]),
                    expression=StLiteral(value=1),
                    line=1,
                ),
                StReturn(line=2),
                StAssignment(
                    target=TagPath(segments=[TagPathSegment(name="b")]),
                    expression=StLiteral(value=2),
                    line=3,
                ),
                StAssignment(
                    target=TagPath(segments=[TagPathSegment(name="c")]),
                    expression=StLiteral(value=3),
                    line=4,
                ),
            ]
        ),
    )
    diags = ws110_dead_code(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 2
