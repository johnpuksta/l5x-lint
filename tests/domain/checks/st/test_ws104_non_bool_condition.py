from l5x_lint.domain.checks.st.ws104_non_bool_condition import ws104_non_bool_condition
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
from l5x_lint.domain.st_models import StIf, StProgram, StTagRef, StWhile
from l5x_lint.domain.symbols import build_symbol_table


def _loc(program="Prog", routine=""):
    return Location(program=program, routine=routine)


def test_if_with_bool_condition_no_diagnostic():
    prog = StProgram(
        statements=[
            StIf(
                condition=StTagRef(path=TagPath(segments=[TagPathSegment(name="ok")])),
                body=[],
                line=1,
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(
        name="Test",
        tags=[Tag(name="ok", data_type="BOOL")],
        data_types=[DataType(name="BOOL", family="", class_="")],
        programs=[Program(name="Prog")],
    )
    table = build_symbol_table(c)
    result = ws104_non_bool_condition(r, table, _loc())
    assert result == []


def test_if_with_dint_condition_emits_ws104():
    prog = StProgram(
        statements=[
            StIf(
                condition=StTagRef(path=TagPath(segments=[TagPathSegment(name="x")])),
                body=[],
                line=1,
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(
        name="Test",
        tags=[Tag(name="x", data_type="DINT")],
        data_types=[DataType(name="DINT", family="", class_="")],
        programs=[Program(name="Prog")],
    )
    table = build_symbol_table(c)
    result = ws104_non_bool_condition(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WS104"


def test_while_with_bool_no_diagnostic():
    prog = StProgram(
        statements=[
            StWhile(
                condition=StTagRef(
                    path=TagPath(segments=[TagPathSegment(name="running")])
                ),
                body=[],
                line=1,
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(
        name="Test",
        tags=[Tag(name="running", data_type="BOOL")],
        data_types=[DataType(name="BOOL", family="", class_="")],
        programs=[Program(name="Prog")],
    )
    table = build_symbol_table(c)
    result = ws104_non_bool_condition(r, table, _loc())
    assert result == []


def test_no_body():
    r = Routine(name="Main", type="ST")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws104_non_bool_condition(r, table, _loc())
    assert result == []


def test_non_st_ignored():
    r = Routine(name="Main", type="RLL")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws104_non_bool_condition(r, table, _loc())
    assert result == []
