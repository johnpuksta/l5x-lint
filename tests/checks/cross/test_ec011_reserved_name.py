from l5x_lint.checks.cross.ec011_reserved_name import _reset, ec011_reserved_name
from l5x_lint.domain.models import AOI, Controller, Location, Routine
from l5x_lint.pipeline.symbols import build_symbol_table


def _loc(program="", routine=""):
    return Location(program=program, routine=routine)


def test_no_aois_no_diagnostic():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec011_reserved_name(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_custom_aoi_name_no_diagnostic():
    c = Controller(name="Test", aois=[AOI(name="MyCustomAOI")])
    table = build_symbol_table(c)
    result = ec011_reserved_name(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_ton_aoi_emits_ec011():
    _reset()
    c = Controller(name="Test", aois=[AOI(name="TON")])
    table = build_symbol_table(c)
    result = ec011_reserved_name(Routine(name="Main", type="RLL"), table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC011"


def test_ctu_aoi_emits_ec011():
    _reset()
    c = Controller(name="Test", aois=[AOI(name="CTU")])
    table = build_symbol_table(c)
    result = ec011_reserved_name(Routine(name="Main", type="RLL"), table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC011"


def test_mixed_reserved_and_custom():
    _reset()
    c = Controller(name="Test", aois=[AOI(name="TON"), AOI(name="MyAOI")])
    table = build_symbol_table(c)
    result = ec011_reserved_name(Routine(name="Main", type="RLL"), table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC011"


def test_no_duplicate_reports():
    _reset()
    c = Controller(name="Test", aois=[AOI(name="TON")])
    table = build_symbol_table(c)
    r1 = ec011_reserved_name(Routine(name="Main", type="RLL"), table, _loc())
    r2 = ec011_reserved_name(Routine(name="Other", type="RLL"), table, _loc())
    assert len(r1) == 1
    assert len(r2) == 0
