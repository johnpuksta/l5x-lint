from l5x_lint.domain.checks.st.ws113_and_then_or_else import ws113_and_then_or_else
from l5x_lint.domain.models import (
    DataType,
    Location,
    Routine,
    Tag,
    TagPath,
    TagPathSegment,
)
from l5x_lint.domain.st_models import StBinaryOp, StProgram, StTagRef
from l5x_lint.domain.symbols import SymbolTable


def _make_bool_tag(name: str) -> Tag:
    return Tag(name=name, data_type="BOOL")


def _make_dint_tag(name: str) -> Tag:
    return Tag(name=name, data_type="DINT")


def _make_ref(name: str) -> StTagRef:
    return StTagRef(path=TagPath(segments=[TagPathSegment(name=name)]))


def test_bool_and_then_no_diagnostic():
    symbols = SymbolTable(
        controller_tags={"A": _make_bool_tag("A"), "B": _make_bool_tag("B")},
        data_types={"BOOL": DataType(name="BOOL", family="", class_="")},
    )
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StBinaryOp(left=_make_ref("A"), op="AND_THEN", right=_make_ref("B")),
            ]
        ),
    )
    diags = ws113_and_then_or_else(r, symbols, Location(program="P", routine="Test"))
    assert diags == []


def test_dint_and_then_emits_ws113():
    symbols = SymbolTable(
        controller_tags={"X": _make_dint_tag("X"), "Y": _make_bool_tag("Y")},
        data_types={
            "DINT": DataType(name="DINT", family="", class_=""),
            "BOOL": DataType(name="BOOL", family="", class_=""),
        },
    )
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StBinaryOp(left=_make_ref("X"), op="AND_THEN", right=_make_ref("Y")),
            ]
        ),
    )
    diags = ws113_and_then_or_else(r, symbols, Location(program="P", routine="Test"))
    assert len(diags) >= 1
    assert diags[0].code == "WS113"


def test_no_body():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ws113_and_then_or_else(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ws113_and_then_or_else(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []
