import importlib

from l5x_lint.domain.checks.cross import ec018_empty_pou
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.symbols import SymbolTable


def _reset():
    importlib.reload(ec018_empty_pou)


def test_non_empty_routine_no_diagnostic():
    _reset()
    symbols = SymbolTable(routine_names={"Test"})
    r = Routine(name="Test", type="RLL", rll_rungs=[object()])
    diags = ec018_empty_pou.ec018_empty_pou(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_empty_routine_emits_ec018():
    _reset()
    symbols = SymbolTable(routine_names={"Test"})
    r = Routine(name="Test", type="RLL", rll_rungs=[], st_body=None, cdata="")
    diags = ec018_empty_pou.ec018_empty_pou(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
    assert diags[0].code == "EC018"
    assert "empty" in diags[0].message.lower() or "no body" in diags[0].message.lower()


def test_no_routines_at_all_emits_ec018():
    _reset()
    symbols = SymbolTable(routine_names=set())
    r = Routine(name="Test", type="RLL", rll_rungs=[], st_body=None, cdata="")
    diags = ec018_empty_pou.ec018_empty_pou(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
    assert "no defined routines" in diags[0].message.lower()


def test_only_cdata_is_body():
    _reset()
    symbols = SymbolTable(routine_names={"Test"})
    r = Routine(
        name="Test", type="ST", st_body=None, rll_rungs=[], cdata="some content"
    )
    diags = ec018_empty_pou.ec018_empty_pou(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_st_body_present_no_diagnostic():
    _reset()
    symbols = SymbolTable(routine_names={"Test"})
    r = Routine(name="Test", type="ST", st_body=object())
    diags = ec018_empty_pou.ec018_empty_pou(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []
