from l5x_lint.checks.cross.wc106_unused_pou import _reset, wc106_unused_pou
from l5x_lint.domain.models import AOI, Controller, Location, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.pipeline.symbols import build_symbol_table


def _loc(program="", routine=""):
    return Location(program=program, routine=routine)


def test_no_aois_no_diagnostic():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = wc106_unused_pou(Routine(name="Main", type="RLL"), table, _loc())
    assert result == []


def test_unused_aoi_emits_wc106():
    _reset()
    c = Controller(name="Test", aois=[AOI(name="UnusedAOI")])
    table = build_symbol_table(c)
    r = Routine(
        name="Main",
        type="RLL",
        rll_rungs=[
            ParsedRung(
                number=0,
                text="",
                instructions=[
                    Instruction(opcode="XIC", operands=[Operand(value="TagA")]),
                ],
            ),
        ],
    )
    result = wc106_unused_pou(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WC106"


def test_used_aoi_no_diagnostic():
    _reset()
    c = Controller(name="Test", aois=[AOI(name="MyAOI")])
    table = build_symbol_table(c)
    r = Routine(
        name="Main",
        type="RLL",
        rll_rungs=[
            ParsedRung(
                number=0,
                text="",
                instructions=[
                    Instruction(opcode="MyAOI", operands=[Operand(value="Inst")]),
                ],
            ),
        ],
    )
    result = wc106_unused_pou(r, table, _loc())
    assert result == []


def test_empty_routine():
    _reset()
    c = Controller(name="Test", aois=[AOI(name="UnusedAOI")])
    table = build_symbol_table(c)
    result = wc106_unused_pou(Routine(name="Main", type="RLL"), table, _loc())
    assert len(result) == 1
