from domain.checks.st.ws107_missing_else import ws107_missing_else
from domain.models import Controller, Location, Routine
from domain.st_models import StCase, StIf, StProgram
from domain.symbols import build_symbol_table


def _loc(program="", routine=""):
    return Location(program=program, routine=routine)


def test_if_with_else_no_diagnostic():
    from domain.models import TagPath, TagPathSegment
    from domain.st_models import StAssignment

    prog = StProgram(
        statements=[
            StIf(
                condition=None,
                body=[],
                else_body=[
                    StAssignment(
                        target=TagPath(segments=[TagPathSegment(name="x")]),
                        expression=None,
                    )
                ],
                line=1,
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws107_missing_else(r, table, _loc())
    assert result == []


def test_if_without_else_emits_ws107():
    prog = StProgram(
        statements=[
            StIf(condition=None, body=[], line=1),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws107_missing_else(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WS107"


def test_case_without_else_emits_ws107():
    prog = StProgram(
        statements=[
            StCase(expression=None, cases=[], line=1),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws107_missing_else(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WS107"


def test_case_with_else_no_diagnostic():
    from domain.models import TagPath, TagPathSegment
    from domain.st_models import StAssignment

    prog = StProgram(
        statements=[
            StCase(
                expression=None,
                cases=[],
                else_body=[
                    StAssignment(
                        target=TagPath(segments=[TagPathSegment(name="x")]),
                        expression=None,
                    )
                ],
                line=1,
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws107_missing_else(r, table, _loc())
    assert result == []


def test_no_body():
    r = Routine(name="Main", type="ST")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws107_missing_else(r, table, _loc())
    assert result == []


def test_non_st_ignored():
    r = Routine(name="Main", type="RLL")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ws107_missing_else(r, table, _loc())
    assert result == []
