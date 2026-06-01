from l5x_lint.domain.checks.cross.wc103_cyclomatic_complexity import (
    wc103_cyclomatic_complexity,
)
from l5x_lint.domain.models import Controller, Location, Routine
from l5x_lint.domain.rll_models import Instruction, ParsedRung
from l5x_lint.domain.st_models import StIf, StProgram
from l5x_lint.domain.symbols import build_symbol_table


def _loc(program="", routine=""):
    return Location(program=program, routine=routine)


def test_st_simple_no_diagnostic():
    prog = StProgram(
        statements=[
            StIf(condition=None, body=[], line=1),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wc103_cyclomatic_complexity(r, table, _loc())
    assert result == []


def test_st_above_threshold():
    branches = []
    for i in range(20):
        branches.append(StIf(condition=None, body=[], line=i))
    prog = StProgram(statements=branches)
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wc103_cyclomatic_complexity(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WC103"
    assert "20" in result[0].message


def test_rll_below_threshold():
    rungs = [ParsedRung(number=0, text="", instructions=[Instruction(opcode="XIC")])]
    r = Routine(name="Main", type="RLL", rll_rungs=rungs)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wc103_cyclomatic_complexity(r, table, _loc())
    assert result == []


def test_rll_above_threshold():
    instructions = [Instruction(opcode="XIC") for _ in range(20)]
    rungs = [
        ParsedRung(number=i, text="", instructions=[inst])
        for i, inst in enumerate(instructions)
    ]
    r = Routine(name="Main", type="RLL", rll_rungs=rungs)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wc103_cyclomatic_complexity(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WC103"


def test_no_body():
    r = Routine(name="Main", type="ST")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wc103_cyclomatic_complexity(r, table, _loc())
    assert result == []
