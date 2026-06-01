from l5x_lint.domain.checks.cross.ec002_type_mismatch import ec002_type_mismatch
from l5x_lint.domain.models import Controller, Location, Routine, Tag
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.application import analyze
from l5x_lint.domain.symbols import build_symbol_table


def _reset_registry():
    analyze._registry.clear()


def _loc(program="Prog", routine="Main", rung=None):
    return Location(program=program, routine=routine, rung=rung)


def _rung(*instructions):
    return ParsedRung(number=0, text="", instructions=list(instructions))


def _inst(opcode, *operand_values):
    return Instruction(
        opcode=opcode, operands=[Operand(value=v) for v in operand_values]
    )


def test_ton_with_timer_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("TON", "MyTimer"))])
    c = Controller(name="Test", tags=[Tag(name="MyTimer", data_type="TIMER")])
    table = build_symbol_table(c)
    result = ec002_type_mismatch(r, table, _loc())
    assert result == []


def test_ton_with_dint_emits_ec002():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("TON", "MyDint"))])
    c = Controller(name="Test", tags=[Tag(name="MyDint", data_type="DINT")])
    table = build_symbol_table(c)
    result = ec002_type_mismatch(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC002"


def test_no_expected_type_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "MyTag"))])
    c = Controller(name="Test", tags=[Tag(name="MyTag", data_type="DINT")])
    table = build_symbol_table(c)
    result = ec002_type_mismatch(r, table, _loc())
    assert result == []


def test_st_call_type_mismatch():
    from l5x_lint.domain.models import TagPath, TagPathSegment
    from l5x_lint.domain.st_models import StCall, StProgram, StTagRef

    prog = StProgram(
        statements=[
            StCall(
                name="TON",
                args=[
                    StTagRef(path=TagPath(segments=[TagPathSegment(name="MyDint")])),
                ],
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test", tags=[Tag(name="MyDint", data_type="DINT")])
    table = build_symbol_table(c)
    result = ec002_type_mismatch(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC002"


def test_unknown_tag_skipped():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("TON", "NoTag"))])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec002_type_mismatch(r, table, _loc())
    assert result == []


def test_ctu_with_counter_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("CTU", "MyCtr"))])
    c = Controller(name="Test", tags=[Tag(name="MyCtr", data_type="COUNTER")])
    table = build_symbol_table(c)
    result = ec002_type_mismatch(r, table, _loc())
    assert result == []


def test_res_with_timer_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("RES", "MyTimer"))])
    c = Controller(name="Test", tags=[Tag(name="MyTimer", data_type="TIMER")])
    table = build_symbol_table(c)
    result = ec002_type_mismatch(r, table, _loc())
    assert result == []


def test_non_rll_ignored():
    r = Routine(name="Main", type="FBD")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec002_type_mismatch(r, table, _loc())
    assert result == []
