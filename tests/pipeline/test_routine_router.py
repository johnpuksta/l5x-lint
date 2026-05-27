from returns.result import Failure, Success

from l5x_lint.domain.models import Controller, Program, Routine
from l5x_lint.domain.rll_models import ParsedRung
from l5x_lint.domain.st_models import StAssignment, StProgram
from l5x_lint.pipeline.routine_router import route_routines


def _controller(routines: list[Routine], prog_name: str = "MainProgram") -> Controller:
    return Controller(
        name="TestPLC",
        programs=[Program(name=prog_name, routines=routines)],
    )


def test_no_programs():
    c = Controller(name="TestPLC")
    result = route_routines(c)
    assert isinstance(result, Success)
    assert result.unwrap() is c


def test_no_routines():
    c = _controller([])
    result = route_routines(c)
    assert isinstance(result, Success)
    assert result.unwrap() is c


def test_empty_cdata():
    c = _controller([Routine(name="Main", type="RLL", cdata="")])
    result = route_routines(c)
    assert isinstance(result, Success)
    r = result.unwrap().programs[0].routines[0]
    assert r.rll_rungs == []
    assert r.st_body is None


def test_rll_routine():
    c = _controller([Routine(name="Main", type="RLL", cdata="XIC(Start)OTE(Run);")])
    result = route_routines(c)
    assert isinstance(result, Success)
    r = result.unwrap().programs[0].routines[0]
    assert len(r.rll_rungs) == 1
    assert isinstance(r.rll_rungs[0], ParsedRung)
    assert r.rll_rungs[0].instructions[0].opcode == "XIC"
    assert r.rll_rungs[0].instructions[0].operands[0].value == "Start"


def test_st_routine():
    c = _controller([Routine(name="Main", type="ST", cdata="x := 42;")])
    result = route_routines(c)
    assert isinstance(result, Success)
    r = result.unwrap().programs[0].routines[0]
    assert isinstance(r.st_body, StProgram)
    assert len(r.st_body.statements) == 1
    assert isinstance(r.st_body.statements[0], StAssignment)
    assert r.st_body.statements[0].expression.value == 42


def test_mixed_rll_and_st():
    c = _controller([
        Routine(name="RLLRoutine", type="RLL", cdata="XIC(A)OTE(B);"),
        Routine(name="STRoutine", type="ST", cdata="x := 1;"),
    ])
    result = route_routines(c)
    assert isinstance(result, Success)
    prog = result.unwrap().programs[0]
    rll_r = prog.routines[0]
    st_r = prog.routines[1]
    assert len(rll_r.rll_rungs) == 1
    assert isinstance(st_r.st_body, StProgram)


def test_multiple_programs():
    c = Controller(
        name="TestPLC",
        programs=[
            Program(name="ProgA", routines=[
                Routine(name="Main", type="RLL", cdata="XIC(A)OTE(B);"),
            ]),
            Program(name="ProgB", routines=[
                Routine(name="Main", type="ST", cdata="y := 99;"),
            ]),
        ],
    )
    result = route_routines(c)
    assert isinstance(result, Success)
    prog_a = result.unwrap().programs[0]
    prog_b = result.unwrap().programs[1]
    assert len(prog_a.routines[0].rll_rungs) == 1
    assert len(prog_b.routines[0].st_body.statements) == 1


def test_unsupported_type_skipped():
    for rtype in ("FBD", "SFC", "FUNCTION", "FUNCTION_BLOCK"):
        c = _controller([Routine(name="Main", type=rtype, cdata="some content")])
        result = route_routines(c)
        assert isinstance(result, Success), f"Failed for type {rtype}"
        r = result.unwrap().programs[0].routines[0]
        assert r.rll_rungs == []
        assert r.st_body is None


def test_rll_parse_error():
    c = _controller([Routine(name="Main", type="RLL", cdata="XIC(")])
    result = route_routines(c)
    assert isinstance(result, Failure)


def test_st_parse_error():
    c = _controller([Routine(name="Main", type="ST", cdata="x := ")])

    result = route_routines(c)
    assert isinstance(result, Failure)


def test_first_failure_stops():
    c = Controller(
        name="TestPLC",
        programs=[
            Program(name="ProgA", routines=[
                Routine(name="R1", type="RLL", cdata="XIC(A)OTE(B);"),
            ]),
            Program(name="ProgB", routines=[
                Routine(name="R2", type="ST", cdata="x := bad syntax;"),
            ]),
            Program(name="ProgC", routines=[
                Routine(name="R3", type="RLL", cdata="XIC(C)OTE(D);"),
            ]),
        ],
    )
    result = route_routines(c)
    assert isinstance(result, Failure)
