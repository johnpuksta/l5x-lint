from l5x_lint.domain.models import TagPath, TagPathSegment
from l5x_lint.domain.st_models import (
    StAssignment,
    StBinaryOp,
    StCall,
    StExit,
    StFor,
    StIf,
    StJsr,
    StLiteral,
    StProgram,
    StRepeat,
    StReturn,
    StTagRef,
    StUnaryOp,
    StWhile,
)


def test_st_program_empty():
    p = StProgram()
    assert p.statements == []


def test_st_program_with_statements():
    target = TagPath([TagPathSegment("x")])
    expr = StLiteral(42)
    stmt = StAssignment(target, expr)
    p = StProgram([stmt])
    assert len(p.statements) == 1


def test_st_assignment():
    target = TagPath([TagPathSegment("x")])
    expr = StBinaryOp(StTagRef(TagPath([TagPathSegment("y")])), "+", StLiteral(1))
    stmt = StAssignment(target, expr, line=1)
    assert stmt.target.full_name == "x"
    assert stmt.line == 1


def test_st_if():
    cond = StTagRef(TagPath([TagPathSegment("x")]))
    body = [StAssignment(TagPath([TagPathSegment("y")]), StLiteral(1), line=2)]
    stmt = StIf(cond, body, line=1)
    assert len(stmt.body) == 1
    assert stmt.line == 1


def test_st_if_else():
    cond = StTagRef(TagPath([TagPathSegment("x")]))
    body = [StAssignment(TagPath([TagPathSegment("y")]), StLiteral(1))]
    else_body = [StAssignment(TagPath([TagPathSegment("z")]), StLiteral(2))]
    stmt = StIf(cond, body, else_body=else_body)
    assert len(stmt.body) == 1
    assert len(stmt.else_body) == 1


def test_st_for():
    var = TagPath([TagPathSegment("i")])
    body = [StAssignment(TagPath([TagPathSegment("x")]), StLiteral(1))]
    stmt = StFor(var, StLiteral(1), StLiteral(10), body=body, line=3)
    assert stmt.variable.full_name == "i"
    assert stmt.line == 3


def test_st_while():
    body = [StAssignment(TagPath([TagPathSegment("x")]), StLiteral(1))]
    stmt = StWhile(StTagRef(TagPath([TagPathSegment("done")])), body)
    assert stmt.condition is not None


def test_st_repeat():
    body = [StAssignment(TagPath([TagPathSegment("x")]), StLiteral(1))]
    stmt = StRepeat(body, until=StTagRef(TagPath([TagPathSegment("done")])))
    assert stmt.until is not None


def test_st_call():
    tmr = StTagRef(TagPath([TagPathSegment("Timer1")]))
    stmt = StCall("TON", [tmr, StLiteral("?"), StLiteral("?")])
    assert stmt.name == "TON"
    assert len(stmt.args) == 3


def test_st_jsr():
    stmt = StJsr("MyRoutine", [StLiteral(42)])
    assert stmt.routine_name == "MyRoutine"
    assert len(stmt.args) == 1


def test_st_exit():
    stmt = StExit(line=5)
    assert stmt.line == 5


def test_st_return():
    stmt = StReturn(line=6)
    assert stmt.line == 6


def test_st_unary_op():
    expr = StUnaryOp("-", StLiteral(5))
    assert expr.op == "-"


def test_st_binary_op():
    expr = StBinaryOp(StLiteral(1), "+", StLiteral(2))
    assert expr.op == "+"


def test_st_tag_ref():
    path = TagPath([TagPathSegment("Conveyor"), TagPathSegment("Speed")])
    ref = StTagRef(path)
    assert ref.path.full_name == "Conveyor.Speed"


def test_st_literal_types():
    assert StLiteral(42).value == 42
    assert StLiteral(3.14).value == 3.14
    assert StLiteral("hello").value == "hello"
    assert StLiteral(True).value is True
