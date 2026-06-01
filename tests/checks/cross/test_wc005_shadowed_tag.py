from l5x_lint.checks.cross.wc005_shadowed_tag import wc005_shadowed_tag
from l5x_lint.domain.models import Controller, Location, Program, Routine, Tag
from l5x_lint.pipeline import analyze
from l5x_lint.pipeline.symbols import build_symbol_table


def _reset_registry():
    analyze._registry.clear()


def _loc(program="Prog", routine="Main", rung=None):
    return Location(program=program, routine=routine, rung=rung)


def test_no_shadowing():
    c = Controller(
        name="Test",
        tags=[Tag(name="CtrlTag", data_type="DINT")],
        programs=[Program(name="Prog", tags=[Tag(name="ProgTag", data_type="BOOL")])],
    )  # noqa: E501
    table = build_symbol_table(c)
    result = wc005_shadowed_tag(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_program_tag_shadows_controller():
    c = Controller(
        name="Test",
        tags=[Tag(name="Shared", data_type="DINT")],
        programs=[Program(name="Prog", tags=[Tag(name="Shared", data_type="BOOL")])],
    )  # noqa: E501
    table = build_symbol_table(c)
    result = wc005_shadowed_tag(Routine(name="Main", type="RLL"), table, _loc())
    assert len(result) == 1
    assert result[0].code == "WC005"


def test_multiple_programs_one_shadow():
    c = Controller(
        name="Test",
        tags=[Tag(name="Shared", data_type="DINT")],
        programs=[
            Program(name="A", tags=[Tag(name="Shared", data_type="BOOL")]),
            Program(name="B"),
        ],
    )
    table = build_symbol_table(c)
    result = wc005_shadowed_tag(Routine(name="Main", type="RLL"), table, _loc())
    assert len(result) == 1


def test_no_controller_tags():
    c = Controller(
        name="Test",
        programs=[Program(name="Prog", tags=[Tag(name="MyTag", data_type="DINT")])],
    )  # noqa: E501
    table = build_symbol_table(c)
    result = wc005_shadowed_tag(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_empty_controller():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wc005_shadowed_tag(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []
