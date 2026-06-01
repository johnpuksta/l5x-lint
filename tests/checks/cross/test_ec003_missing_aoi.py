from l5x_lint.checks.cross.ec003_missing_aoi import ec003_missing_aoi
from l5x_lint.domain.models import AOI, Controller, Location, Routine, Tag
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.pipeline import analyze
from l5x_lint.pipeline.symbols import build_symbol_table


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


def test_builtin_opcode_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "TagA"))])
    c = Controller(name="Test", tags=[Tag(name="TagA", data_type="DINT")])
    table = build_symbol_table(c)
    result = ec003_missing_aoi(r, table, _loc())
    assert result == []


def test_defined_aoi_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("MyAOI", "Param1"))])
    c = Controller(name="Test", aois=[AOI(name="MyAOI")])
    table = build_symbol_table(c)
    result = ec003_missing_aoi(r, table, _loc())
    assert result == []


def test_undefined_aoi_emits_ec003():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("NoSuchAOI"))])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec003_missing_aoi(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC003"


def test_non_rll_ignored():
    r = Routine(name="Main", type="FBD")
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec003_missing_aoi(r, table, _loc())
    assert result == []


def test_st_call_undefined_aoi():
    from l5x_lint.domain.st_models import StCall, StProgram

    prog = StProgram(statements=[StCall(name="NoSuchAOI")])
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec003_missing_aoi(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC003"


def test_st_call_builtin_skipped():
    from l5x_lint.domain.st_models import StCall, StProgram

    prog = StProgram(statements=[StCall(name="TON")])
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec003_missing_aoi(r, table, _loc())
    assert result == []
