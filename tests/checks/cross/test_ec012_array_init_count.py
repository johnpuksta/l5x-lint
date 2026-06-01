from l5x_lint.checks.cross.ec012_array_init_count import _reset, ec012_array_init_count
from l5x_lint.domain.models import Controller, Location, Routine, Tag
from l5x_lint.domain.symbols import build_symbol_table


def _loc(program="", routine=""):
    return Location(program=program, routine=routine)


def test_no_array_tags_no_diagnostic():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec012_array_init_count(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_correct_init_count_no_diagnostic():
    c = Controller(
        name="Test",
        tags=[Tag(name="Arr", data_type="DINT", dimensions=(5,), initial_values=5)],
    )
    table = build_symbol_table(c)
    result = ec012_array_init_count(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_wrong_init_count_emits_ec012():
    _reset()
    c = Controller(
        name="Test",
        tags=[Tag(name="Arr", data_type="DINT", dimensions=(5,), initial_values=3)],
    )
    table = build_symbol_table(c)
    result = ec012_array_init_count(Routine(name="Main", type="RLL"), table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC012"


def test_multi_dim_array_wrong_init():
    _reset()
    c = Controller(
        name="Test",
        tags=[Tag(name="Mat", data_type="DINT", dimensions=(2, 3), initial_values=3)],
    )
    table = build_symbol_table(c)
    result = ec012_array_init_count(Routine(name="Main", type="RLL"), table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC012"


def test_no_duplicate_reports():
    _reset()
    c = Controller(
        name="Test",
        tags=[Tag(name="Arr", data_type="DINT", dimensions=(5,), initial_values=3)],
    )
    table = build_symbol_table(c)
    r1 = ec012_array_init_count(Routine(name="Main", type="RLL"), table, _loc())
    r2 = ec012_array_init_count(Routine(name="Other", type="RLL"), table, _loc())
    assert len(r1) == 1
    assert len(r2) == 0
