from returns.result import Failure

from domain.st_models import (
    StAssignment,
    StBinaryOp,
    StCall,
    StCase,
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
from infrastructure.st_parser import parse


def test_empty_text():
    result = parse("")
    prog = result.unwrap()
    assert isinstance(prog, StProgram)
    assert prog.statements == []


def test_whitespace_only():
    result = parse("  \n  ")
    prog = result.unwrap()
    assert prog.statements == []


def test_simple_assignment():
    result = parse("x := 42;")
    prog = result.unwrap()
    assert len(prog.statements) == 1
    stmt = prog.statements[0]
    assert isinstance(stmt, StAssignment)
    assert stmt.target.segments[0].name == "x"
    assert stmt.expression.value == 42


def test_tag_ref_assignment():
    result = parse("x := y;")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt.expression, StTagRef)


def test_binary_op():
    result = parse("x := y + 1;")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StBinaryOp)
    assert expr.op == "+"


def test_precedence_mul_over_add():
    result = parse("x := a + b * c;")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StBinaryOp)
    assert expr.op == "+"
    assert isinstance(expr.right, StBinaryOp)
    assert expr.right.op == "*"


def test_parentheses():
    result = parse("x := (a + b) * c;")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StBinaryOp)
    assert expr.op == "*"
    assert isinstance(expr.left, StBinaryOp)
    assert expr.left.op == "+"


def test_negation():
    result = parse("x := -y;")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StUnaryOp)
    assert expr.op == "-"


def test_logical_not():
    result = parse("x := not y;")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StUnaryOp)
    assert expr.op == "not"


def test_compare_operators():
    for op in ("=", "<>", "<", ">", "<=", ">="):
        text = f"x := a {op} b;"
        result = parse(text)
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp), f"Failed for {op}"
        assert expr.op == op, f"Expected {op}, got {expr.op}"


def test_logical_operators():
    result = parse("x := a or b and c;")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StBinaryOp)
    assert expr.op == "or"


def test_if_simple():
    result = parse("if x then y := 1; end_if")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StIf)
    assert isinstance(stmt.condition, StTagRef)
    assert len(stmt.body) == 1


def test_if_else():
    result = parse("if x then y := 1; else y := 2; end_if")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert len(stmt.body) == 1
    assert len(stmt.else_body) == 1


def test_if_elsif():
    result = parse("if x then y := 1; elsif z then y := 2; end_if")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert len(stmt.body) == 1
    assert len(stmt.elsif_pairs) == 1
    assert isinstance(stmt.elsif_pairs[0][0], StTagRef)
    assert len(stmt.elsif_pairs[0][1]) == 1


def test_if_multi_body():
    result = parse("if x then a := 1; b := 2; end_if")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert len(stmt.body) == 2


def test_if_elsif_else():
    result = parse("if x then a:=1; elsif y then b:=2; else c:=3; end_if")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert len(stmt.body) == 1
    assert len(stmt.elsif_pairs) == 1
    assert len(stmt.else_body) == 1


def test_for_loop():
    result = parse("for i := 1 to 10 do x := x + 1; end_for")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StFor)
    assert stmt.variable.segments[0].name == "i"
    assert stmt.start.value == 1
    assert stmt.end.value == 10
    assert stmt.step is None
    assert len(stmt.body) == 1


def test_for_loop_with_step():
    result = parse("for i := 1 to 10 by 2 do x := x + 1; end_for")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert stmt.step is not None
    assert stmt.step.value == 2


def test_while_loop():
    result = parse("while x < 10 do x := x + 1; end_while")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StWhile)
    assert isinstance(stmt.condition, StBinaryOp)
    assert len(stmt.body) == 1


def test_repeat_loop():
    result = parse("repeat x := x + 1; until x >= 10 end_repeat")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StRepeat)
    assert len(stmt.body) == 1
    assert isinstance(stmt.until, StBinaryOp)


def test_repeat_multi_body():
    result = parse("repeat a:=1; b:=2; until c end_repeat")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert len(stmt.body) == 2


def test_call_timer():
    result = parse("TON(Timer1, ?, ?);")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StCall)
    assert stmt.name == "TON"
    assert len(stmt.args) == 3
    assert isinstance(stmt.args[0], StTagRef)
    assert isinstance(stmt.args[1], StLiteral)
    assert stmt.args[1].value == "?"


def test_call_nested():
    result = parse("x := MAX(a, b);")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StCall)
    assert expr.name == "MAX"
    assert len(expr.args) == 2


def test_jsr_call():
    result = parse("JSR(MyRoutine, Param1);")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StJsr)
    assert stmt.routine_name == "MyRoutine"
    assert len(stmt.args) == 1


def test_jsr_no_args():
    result = parse("JSR(MyRoutine);")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StJsr)
    assert stmt.routine_name == "MyRoutine"
    assert stmt.args == []


def test_exit_statement():
    result = parse("exit;")
    prog = result.unwrap()
    assert isinstance(prog.statements[0], StExit)


def test_return_statement():
    result = parse("return;")
    prog = result.unwrap()
    assert isinstance(prog.statements[0], StReturn)


def test_member_access():
    result = parse("x := Timer1.DN;")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StTagRef)
    assert expr.path.segments[0].name == "Timer1"
    assert expr.path.segments[1].name == "DN"


def test_array_index():
    result = parse("x := Arr[5];")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StTagRef)
    assert expr.path.segments[0].name == "Arr"
    assert expr.path.segments[0].index == 5


def test_array_member():
    result = parse("x := Arr[2].Member;")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    segs = expr.path.segments
    assert segs[0].name == "Arr"
    assert segs[0].index == 2
    assert segs[1].name == "Member"


def test_float_literal():
    result = parse("x := 3.14;")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StLiteral)
    assert expr.value == 3.14


def test_bool_literals():
    for val in ("true", "false"):
        result = parse(f"x := {val};")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert isinstance(expr.value, bool)


def test_mixed_complex():
    text = """if Motor_Run and Safety_Ok then
    Timer1.PRE := 5000;
    TON(Timer1, ?, ?);
    Motor_Run := 1;
else
    Motor_Run := 0;
end_if"""
    result = parse(text)
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StIf)
    assert isinstance(stmt.condition, StBinaryOp)
    assert len(stmt.body) == 3
    assert len(stmt.else_body) == 1


def test_parse_invalid_syntax():
    result = parse("x := ;")
    assert isinstance(result, Failure)


def test_parse_garbage():
    result = parse("@#!invalid")
    assert isinstance(result, Failure)


def test_block_comment_c_style():
    result = parse("/* block comment */ x := 1;")
    prog = result.unwrap()
    assert len(prog.statements) == 1
    stmt = prog.statements[0]
    assert isinstance(stmt, StAssignment)
    assert stmt.target.segments[0].name == "x"
    assert stmt.expression.value == 1


def test_block_comment_multiline():
    text = "/* line 1\n   line 2 */\nx := 2;"
    result = parse(text)
    prog = result.unwrap()
    assert len(prog.statements) == 1


def test_block_comment_nested_parens():
    text = "/* has (parens) inside */ x := 1;"
    result = parse(text)
    prog = result.unwrap()
    assert len(prog.statements) == 1


def test_single_quoted_string():
    result = parse("x := 'hello';")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StAssignment)
    assert isinstance(stmt.expression, StLiteral)
    assert stmt.expression.value == "hello"


def test_single_quoted_string_empty():
    result = parse("x := '';")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt.expression, StLiteral)
    assert stmt.expression.value == ""


def test_single_quoted_string_struct_member():
    result = parse("Config.Mode := 'AUTO';")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StAssignment)
    assert stmt.target.segments[0].name == "Config"
    assert stmt.target.segments[1].name == "Mode"
    assert isinstance(stmt.expression, StLiteral)
    assert stmt.expression.value == "AUTO"


def test_single_quoted_string_escaped_quote():
    result = parse("x := 'it''s';")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt.expression, StLiteral)
    assert stmt.expression.value == "it's"


def test_end_if_with_semicolon():
    result = parse("if x then y := 1; end_if;")
    prog = result.unwrap()
    assert len(prog.statements) == 1
    stmt = prog.statements[0]
    assert isinstance(stmt, StIf)
    assert len(stmt.body) == 1


def test_end_if_without_semicolon():
    result = parse("if x then y := 1; end_if")
    prog = result.unwrap()
    assert len(prog.statements) == 1
    assert isinstance(prog.statements[0], StIf)


def test_end_case_with_semicolon():
    result = parse("case x of 1: y := 2; end_case;")
    prog = result.unwrap()
    assert len(prog.statements) == 1
    assert isinstance(prog.statements[0], StCase)


def test_end_for_with_semicolon():
    result = parse("for i := 1 to 10 do x := 1; end_for;")
    prog = result.unwrap()
    assert len(prog.statements) == 1
    assert isinstance(prog.statements[0], StFor)


def test_end_while_with_semicolon():
    result = parse("while x do y := 1; end_while;")
    prog = result.unwrap()
    assert len(prog.statements) == 1
    assert isinstance(prog.statements[0], StWhile)


def test_end_repeat_with_semicolon():
    result = parse("repeat y := 1; until x end_repeat;")
    prog = result.unwrap()
    assert len(prog.statements) == 1
    assert isinstance(prog.statements[0], StRepeat)


def test_region_directive():
    result = parse("#region MyRegion\nx := 1;\n#endregion")
    prog = result.unwrap()
    assert len(prog.statements) == 1
    assert isinstance(prog.statements[0], StAssignment)


def test_region_directive_with_name():
    result = parse("#region Test Region\nval := 1;\n#endregion Test Region")
    prog = result.unwrap()
    assert len(prog.statements) == 1


def test_variable_array_index():
    result = parse("val := DataBuf[Idx];")
    prog = result.unwrap()
    stmt = prog.statements[0]
    assert isinstance(stmt, StAssignment)
    expr = stmt.expression
    assert isinstance(expr, StTagRef)
    assert expr.path.segments[0].name == "DataBuf"
    assert expr.path.segments[1].name == "Idx"


def test_variable_array_index_member():
    result = parse("val := Stack.Items[Idx];")
    prog = result.unwrap()
    expr = prog.statements[0].expression
    assert isinstance(expr, StTagRef)
    segs = expr.path.segments
    assert segs[0].name == "Stack"
    assert segs[1].name == "Items"
    assert segs[1].index is None
    assert segs[2].name == "Idx"


def test_comment_only_routine():
    result = parse("/* entire routine is commented out */")
    prog = result.unwrap()
    assert isinstance(prog, StProgram)
    assert prog.statements == []


def test_comment_only_with_multiple_comments():
    text = "/* first comment */\n/* second comment */"
    result = parse(text)
    prog = result.unwrap()
    assert prog.statements == []


def test_mixed_block_and_line_comments():
    text = "/* block */\n// line comment\nx := 1;"
    result = parse(text)
    prog = result.unwrap()
    assert len(prog.statements) == 1
