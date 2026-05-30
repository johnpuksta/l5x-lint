from l5x_lint.checks.cross.ec008_aoi_circular_dep import ec008_aoi_circular_dep
from l5x_lint.domain.models import AOI, Controller, Location, Routine
from l5x_lint.pipeline import analyze
from l5x_lint.pipeline.symbols import build_symbol_table


def _reset_registry():
    analyze._registry.clear()


def _loc(program="", routine="", rung=None):
    return Location(program=program, routine=routine, rung=rung)


def test_no_aois():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec008_aoi_circular_dep(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_single_aoi_no_cycle():
    c = Controller(name="Test", aois=[AOI(name="MyAOI")])
    table = build_symbol_table(c)
    result = ec008_aoi_circular_dep(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_empty_controller():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec008_aoi_circular_dep(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []
