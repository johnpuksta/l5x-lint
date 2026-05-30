from l5x_lint.checks.st.ws108_no_effect import ws108_no_effect
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StCall, StLiteral, StProgram
from l5x_lint.pipeline.symbols import SymbolTable


def test_no_effect_call_emits_ws108():
    r = Routine(name="Test", type="ST",
                st_body=StProgram(statements=[
                    StCall(name="ADD", args=[StLiteral(value=1), StLiteral(value=2)], line=5),
                ]))
    diags = ws108_no_effect(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "WS108"
    assert diags[0].location.line == 5


def test_effectful_call_no_diagnostic():
    r = Routine(name="Test", type="ST",
                st_body=StProgram(statements=[
                    StCall(name="TON", args=[], line=3),
                ]))
    diags = ws108_no_effect(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_no_body():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ws108_no_effect(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ws108_no_effect(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []
