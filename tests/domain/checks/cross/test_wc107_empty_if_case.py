from domain.checks.cross.wc107_empty_if_case import wc107_empty_body
from domain.models import Location, Routine, TagPath, TagPathSegment
from domain.st_models import (
    StAssignment,
    StCase,
    StIf,
    StLiteral,
    StProgram,
)
from domain.symbols import SymbolTable


def _make_st_routine(body_stmts) -> Routine:
    return Routine(name="Test", type="ST", st_body=StProgram(statements=body_stmts))


def test_if_with_body_no_diagnostic():
    r = _make_st_routine(
        [
            StIf(
                condition=StLiteral(value=True),
                body=[
                    StAssignment(
                        target=TagPath(segments=[TagPathSegment(name="X")]),
                        expression=StLiteral(value=1),
                    )
                ],
                line=1,
            ),
        ]
    )
    diags = wc107_empty_body(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_empty_if_body_emits_wc107():
    r = _make_st_routine(
        [
            StIf(condition=StLiteral(value=True), body=[], line=3),
        ]
    )
    diags = wc107_empty_body(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "WC107"
    assert "IF" in diags[0].message


def test_empty_elsif_body():
    r = _make_st_routine(
        [
            StIf(
                condition=StLiteral(value=True),
                body=[
                    StAssignment(
                        target=TagPath(segments=[TagPathSegment(name="X")]),
                        expression=StLiteral(value=1),
                    )
                ],
                elsif_pairs=[(StLiteral(value=False), [])],
                line=5,
            ),
        ]
    )
    diags = wc107_empty_body(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert "ELSIF" in diags[0].message


def test_empty_case_branch():
    r = _make_st_routine(
        [
            StCase(
                expression=StLiteral(value=1),
                cases=[
                    ([StLiteral(value=1)], []),
                    ([StLiteral(value=2)], [StLiteral(value=42)]),
                ],
                line=7,
            ),
        ]
    )
    diags = wc107_empty_body(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert "CASE" in diags[0].message


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = wc107_empty_body(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_no_body():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = wc107_empty_body(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []
