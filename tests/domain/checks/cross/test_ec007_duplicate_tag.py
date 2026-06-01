from domain.checks.cross.ec007_duplicate_tag import ec007_duplicate_tag
from domain.models import Controller, Location, Routine, Tag
from application import analyze
from domain.symbols import build_symbol_table


def _reset_registry():
    analyze._registry.clear()


def _loc(program="Prog", routine="Main", rung=None):
    return Location(program=program, routine=routine, rung=rung)


def test_no_duplicates():
    c = Controller(
        name="Test",
        tags=[
            Tag(name="A", data_type="DINT"),
            Tag(name="B", data_type="BOOL"),
        ],
    )
    table = build_symbol_table(c)
    result = ec007_duplicate_tag(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_duplicate_controller_tags():
    c = Controller(
        name="Test",
        tags=[
            Tag(name="A", data_type="DINT"),
            Tag(name="a", data_type="BOOL"),
        ],
    )
    table = build_symbol_table(c)
    result = ec007_duplicate_tag(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_empty_controller():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec007_duplicate_tag(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []
