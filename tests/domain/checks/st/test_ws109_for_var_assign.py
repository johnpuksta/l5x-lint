from domain.checks.st.ws109_for_var_assign import ws109_for_var_assign
from domain.models import Location, Routine, TagPath, TagPathSegment
from domain.st_models import (
    StAssignment,
    StFor,
    StLiteral,
    StProgram,
)
from domain.symbols import SymbolTable


def test_for_var_not_assigned_no_diagnostic():
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StFor(
                    variable=TagPath(segments=[TagPathSegment(name="i")]),
                    start=StLiteral(value=1),
                    end=StLiteral(value=10),
                    body=[
                        StAssignment(
                            target=TagPath(segments=[TagPathSegment(name="x")]),
                            expression=StLiteral(value=1),
                        )
                    ],
                ),
            ]
        ),
    )
    diags = ws109_for_var_assign(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_for_var_assigned_emits_ws109():
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StFor(
                    variable=TagPath(segments=[TagPathSegment(name="i")]),
                    start=StLiteral(value=1),
                    end=StLiteral(value=10),
                    body=[
                        StAssignment(
                            target=TagPath(segments=[TagPathSegment(name="i")]),
                            expression=StLiteral(value=5),
                            line=7,
                        )
                    ],
                ),
            ]
        ),
    )
    diags = ws109_for_var_assign(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "WS109"


def test_no_body():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ws109_for_var_assign(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ws109_for_var_assign(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []
