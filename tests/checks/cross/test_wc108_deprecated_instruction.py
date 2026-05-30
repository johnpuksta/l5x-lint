from l5x_lint.checks.cross.wc108_deprecated_instruction import (
    wc108_rll_deprecated,
    wc108_st_deprecated,
)
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.domain.st_models import StCall, StLiteral, StProgram
from l5x_lint.pipeline.symbols import SymbolTable


def test_st_deprecated_call_emits_wc108():
    r = Routine(name="Test", type="ST",
                st_body=StProgram(statements=[
                    StCall(name="MSG", args=[StLiteral(value="hello")], line=4),
                ]))
    diags = wc108_st_deprecated(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "WC108"
    assert "MSG" in diags[0].message


def test_st_non_deprecated_no_diagnostic():
    r = Routine(name="Test", type="ST",
                st_body=StProgram(statements=[
                    StCall(name="TON", args=[], line=2),
                ]))
    diags = wc108_st_deprecated(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_rll_deprecated_instruction_emits_wc108():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        ParsedRung(number=3, text="", instructions=[
            Instruction(opcode="MSG", operands=[Operand(value="MyMsg")]),
        ]),
    ])
    diags = wc108_rll_deprecated(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "WC108"


def test_rll_non_deprecated_no_diagnostic():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        ParsedRung(number=1, text="", instructions=[
            Instruction(opcode="XIC", operands=[Operand(value="A")]),
        ]),
    ])
    diags = wc108_rll_deprecated(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_st_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = wc108_st_deprecated(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_rll_non_rll_ignored():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = wc108_rll_deprecated(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_st_no_body():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = wc108_st_deprecated(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_deprecated_in_branch():
    r = Routine(name="Test", type="RLL", rll_rungs=[
        ParsedRung(number=2, text="", instructions=[
            Instruction(opcode="XIC", operands=[Operand(value="A")],
                        branch=[[Instruction(opcode="PID", operands=[])]]),
        ]),
    ])
    diags = wc108_rll_deprecated(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
