from domain.checks.cross.ec004_invalid_subroutine import ec004_invalid_subroutine
from domain.models import Controller, Location, Program, Routine
from domain.rll_models import Instruction, Operand, ParsedRung
from application import analyze
from domain.symbols import build_symbol_table


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


def test_valid_jsr_no_diagnostic():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("JSR", "SubRoutine"))])
    c = Controller(
        name="Test",
        programs=[
            Program(name="Prog", routines=[Routine(name="SubRoutine", type="RLL")])
        ],
    )  # noqa: E501
    table = build_symbol_table(c)
    result = ec004_invalid_subroutine(r, table, _loc())
    assert result == []


def test_invalid_jsr_emits_ec004():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("JSR", "NoSuch"))])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec004_invalid_subroutine(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC004"


def test_jxr_valid():
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("JXR", "SubRoutine"))])
    c = Controller(
        name="Test",
        programs=[
            Program(name="Prog", routines=[Routine(name="SubRoutine", type="RLL")])
        ],
    )  # noqa: E501
    table = build_symbol_table(c)
    result = ec004_invalid_subroutine(r, table, _loc())
    assert result == []


def test_st_jsr_valid():
    from domain.st_models import StJsr, StProgram

    prog = StProgram(statements=[StJsr(routine_name="SubRoutine")])
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(
        name="Test",
        programs=[
            Program(name="Prog", routines=[Routine(name="SubRoutine", type="ST")])
        ],
    )  # noqa: E501
    table = build_symbol_table(c)
    result = ec004_invalid_subroutine(r, table, _loc())
    assert result == []


def test_st_jsr_invalid():
    from domain.st_models import StJsr, StProgram

    prog = StProgram(statements=[StJsr(routine_name="NoSuch")])
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec004_invalid_subroutine(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "EC004"


def test_empty_routine():
    r = Routine(name="Main", type="RLL", rll_rungs=[])
    c = Controller(name="Test")
    table = build_symbol_table(c)
    result = ec004_invalid_subroutine(r, table, _loc())
    assert result == []
