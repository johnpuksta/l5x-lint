from l5x_lint.checks.st.es001_invalid_expression_op import es001_invalid_expression_op
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


def _make_string_tag(name: str) -> Tag:
    return Tag(name=name, data_type="STRING")


def _make_dint_tag(name: str) -> Tag:
    return Tag(name=name, data_type="DINT")


def _make_ref(name: str) -> StTagRef:
    return StTagRef(path=TagPath(segments=[TagPathSegment(name=name)]))


def test_string_plus_dint_emits_es001():
    symbols = SymbolTable(
        controller_tags={"S": _make_string_tag("S"), "X": _make_dint_tag("X")},
        data_types={
            "STRING": DataType(name="STRING", family="", class_=""),
            "DINT": DataType(name="DINT", family="", class_=""),
        },
    )
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StBinaryOp(left=_make_ref("S"), op="+", right=_make_ref("X")),
            ]
        ),
    )
    diags = es001_invalid_expression_op(
        r, symbols, Location(program="P", routine="Test")
    )
    assert len(diags) >= 1
    assert diags[0].code == "ES001"


def test_dint_plus_dint_no_diagnostic():
    symbols = SymbolTable(
        controller_tags={"A": _make_dint_tag("A"), "B": _make_dint_tag("B")},
        data_types={"DINT": DataType(name="DINT", family="", class_="")},
    )
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StBinaryOp(left=_make_ref("A"), op="+", right=_make_ref("B")),
            ]
        ),
    )
    diags = es001_invalid_expression_op(
        r, symbols, Location(program="P", routine="Test")
    )
    assert diags == []


def test_no_body():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = es001_invalid_expression_op(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = es001_invalid_expression_op(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []
