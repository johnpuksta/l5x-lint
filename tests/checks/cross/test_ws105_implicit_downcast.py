from l5x_lint.checks.cross.ws105_implicit_downcast import ws105_implicit_downcast
from l5x_lint.domain.models import (
    Controller,
    DataType,
    Location,
    Program,
    Routine,
    Tag,
    TagPath,
    TagPathSegment,
)
from l5x_lint.domain.st_models import StAssignment, StProgram, StTagRef
from l5x_lint.domain.symbols import build_symbol_table


def _loc(program="Prog", routine=""):
    return Location(program=program, routine=routine)


def test_lint_to_dint_downcast_emits_ws105():
    prog = StProgram(
        statements=[
            StAssignment(
                target=TagPath(segments=[TagPathSegment(name="narrow")]),
                expression=StTagRef(
                    path=TagPath(segments=[TagPathSegment(name="wide")])
                ),
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(
        name="Test",
        tags=[Tag(name="narrow", data_type="DINT"), Tag(name="wide", data_type="LINT")],
        data_types=[
            DataType(name="DINT", family="", class_=""),
            DataType(name="LINT", family="", class_=""),
        ],
        programs=[Program(name="Prog")],
    )
    table = build_symbol_table(c)
    result = ws105_implicit_downcast(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WS105"


def test_dint_to_lint_widen_no_diagnostic():
    prog = StProgram(
        statements=[
            StAssignment(
                target=TagPath(segments=[TagPathSegment(name="wide")]),
                expression=StTagRef(
                    path=TagPath(segments=[TagPathSegment(name="narrow")])
                ),
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(
        name="Test",
        tags=[Tag(name="narrow", data_type="DINT"), Tag(name="wide", data_type="LINT")],
        data_types=[
            DataType(name="DINT", family="", class_=""),
            DataType(name="LINT", family="", class_=""),
        ],
        programs=[Program(name="Prog")],
    )
    table = build_symbol_table(c)
    result = ws105_implicit_downcast(r, table, _loc())
    assert result == []


def test_same_type_no_diagnostic():
    prog = StProgram(
        statements=[
            StAssignment(
                target=TagPath(segments=[TagPathSegment(name="a")]),
                expression=StTagRef(path=TagPath(segments=[TagPathSegment(name="b")])),
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(
        name="Test",
        tags=[Tag(name="a", data_type="DINT"), Tag(name="b", data_type="DINT")],
        data_types=[DataType(name="DINT", family="", class_="")],
        programs=[Program(name="Prog")],
    )
    table = build_symbol_table(c)
    result = ws105_implicit_downcast(r, table, _loc())
    assert result == []


def test_non_st_ignored():
    r = Routine(name="Main", type="RLL")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws105_implicit_downcast(r, table, _loc())
    assert result == []
