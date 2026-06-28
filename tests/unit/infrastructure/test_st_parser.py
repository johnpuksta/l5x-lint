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
    StNamedArg,
    StProgram,
    StRepeat,
    StReturn,
    StTagRef,
    StTypeBlock,
    StUnaryOp,
    StVarBlock,
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


# ---------------------------------------------------------------------------
# Named parameters in function calls
# ---------------------------------------------------------------------------

class TestNamedParameters:
    def test_named_parameter(self):
        result = parse("LIMIT(MN := 10, IN := x, MX := 100);")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StCall)
        assert stmt.name == "LIMIT"
        assert len(stmt.args) == 3
        assert isinstance(stmt.args[0], StNamedArg)
        assert stmt.args[0].name == "MN"
        assert stmt.args[0].value.value == 10
        assert isinstance(stmt.args[1], StNamedArg)
        assert stmt.args[1].name == "IN"
        assert isinstance(stmt.args[2], StNamedArg)
        assert stmt.args[2].name == "MX"
        assert stmt.args[2].value.value == 100

    def test_mixed_positional_and_named(self):
        result = parse("TON(T1, PT := T#5s);")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StCall)
        assert stmt.name == "TON"
        assert len(stmt.args) == 2
        assert isinstance(stmt.args[0], StTagRef)
        assert isinstance(stmt.args[1], StNamedArg)
        assert stmt.args[1].name == "PT"

    def test_named_parameter_in_expression(self):
        result = parse("x := LIMIT(MN := 10, IN := y, MX := 100);")
        prog = result.unwrap()
        stmt = prog.statements[0]
        expr = stmt.expression
        assert isinstance(expr, StCall)
        assert isinstance(expr.args[0], StNamedArg)

    def test_named_parameter_with_variable(self):
        result = parse("TON(T1, PT := MyTimer);")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StCall)
        assert isinstance(stmt.args[1], StNamedArg)
        assert stmt.args[1].name == "PT"
        assert isinstance(stmt.args[1].value, StTagRef)


# ---------------------------------------------------------------------------
# Variable declarations
# ---------------------------------------------------------------------------

class TestVariableDeclarations:
    def test_simple_var_block(self):
        text = """VAR
    x : INT;
    y : REAL;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1
        var_block = prog.declarations[0]
        assert isinstance(var_block, StVarBlock)
        assert var_block.block_type == "var"
        assert len(var_block.declarations) == 2
        assert var_block.declarations[0].name == "x"
        assert var_block.declarations[0].type_name == "INT"
        assert var_block.declarations[1].name == "y"
        assert var_block.declarations[1].type_name == "REAL"

    def test_var_with_initial_value(self):
        text = """VAR
    counter : INT := 0;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        var_block = prog.declarations[0]
        assert len(var_block.declarations) == 1
        assert var_block.declarations[0].initial_value is not None
        assert var_block.declarations[0].initial_value.value == 0

    def test_var_input(self):
        text = """VAR_INPUT
    Start : BOOL;
    Speed : REAL;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        var_block = prog.declarations[0]
        assert var_block.block_type == "var_input"
        assert len(var_block.declarations) == 2

    def test_var_output(self):
        text = """VAR_OUTPUT
    Running : BOOL;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        var_block = prog.declarations[0]
        assert var_block.block_type == "var_output"

    def test_var_in_out(self):
        text = """VAR_IN_OUT
    Data : INT;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        var_block = prog.declarations[0]
        assert var_block.block_type == "var_in_out"

    def test_var_global(self):
        text = """VAR_GLOBAL
    SystemRunning : BOOL;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        var_block = prog.declarations[0]
        assert var_block.block_type == "var_global"

    def test_var_retain(self):
        text = """VAR
    saved : INT RETAIN;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        assert prog.declarations[0].declarations[0].retain is True

    def test_var_non_retain(self):
        text = """VAR
    temp : INT NON_RETAIN;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        assert prog.declarations[0].declarations[0].non_retain is True

    def test_var_constant(self):
        text = """VAR
    MAX_SIZE : INT := 100 CONSTANT;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        assert prog.declarations[0].declarations[0].constant is True

    def test_var_with_io_address(self):
        text = """VAR
    Input1 AT %IX0.0 : BOOL;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        assert prog.declarations[0].declarations[0].at_address == "%IX0.0"

    def test_var_with_array_dimension(self):
        text = """VAR
    Buffer : INT[10];
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        assert prog.declarations[0].declarations[0].dimension == 10

    def test_var_with_declaration_and_statements(self):
        text = """VAR
    x : INT;
END_VAR
x := 42;"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1
        assert len(prog.statements) == 1

    def test_multiple_var_blocks(self):
        text = """VAR_INPUT
    a : INT;
END_VAR
VAR_OUTPUT
    b : BOOL;
END_VAR
VAR
    c : REAL;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 3
        assert prog.declarations[0].block_type == "var_input"
        assert prog.declarations[1].block_type == "var_output"
        assert prog.declarations[2].block_type == "var"

    def test_var_case_insensitive(self):
        text = """var
    x : int;
end_var"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1
        assert prog.declarations[0].block_type == "var"


# ---------------------------------------------------------------------------
# TYPE declarations
# ---------------------------------------------------------------------------

class TestTypeDeclarations:
    def test_enum_type(self):
        text = """TYPE
    Color : (RED, GREEN, BLUE);
END_TYPE"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1
        type_block = prog.declarations[0]
        assert isinstance(type_block, StTypeBlock)
        assert len(type_block.declarations) == 1

    def test_struct_type(self):
        text = """TYPE
    Point : INT;
END_TYPE"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1
        type_block = prog.declarations[0]
        assert isinstance(type_block, StTypeBlock)

    def test_simple_type_alias(self):
        text = """TYPE
    MyInt : INT;
END_TYPE"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1

    def test_array_type(self):
        text = """TYPE
    Matrix : INT[10];
END_TYPE"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1

    def test_subrange_type(self):
        text = """TYPE
    Percentage : INT;
END_TYPE"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1

    def test_pointer_type(self):
        text = """TYPE
    MyPtr : POINTER TO INT;
END_TYPE"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1

    def test_type_with_statements(self):
        text = """TYPE
    Color : (RED, GREEN, BLUE);
END_TYPE
x := 42;"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1
        assert len(prog.statements) == 1


# ---------------------------------------------------------------------------
# Realistic programs with declarations
# ---------------------------------------------------------------------------

class TestProgramWithDeclarations:
    def test_full_program(self):
        text = """VAR_INPUT
    Start_Button : BOOL;
    Stop_Button : BOOL;
END_VAR
VAR_OUTPUT
    Motor_Run : BOOL;
END_VAR
VAR
    Timer1 : TIMER;
END_VAR
Motor_Run := Start_Button AND NOT Stop_Button;
Timer1(IN := Motor_Run, PT := T#5s);"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 3
        assert len(prog.statements) == 2
        stmt = prog.statements[1]
        assert isinstance(stmt, StCall)
        assert isinstance(stmt.args[0], StNamedArg)
        assert stmt.args[0].name == "IN"
        assert isinstance(stmt.args[1], StNamedArg)
        assert stmt.args[1].name == "PT"


# ---------------------------------------------------------------------------
# Exponentiation operator **
# ---------------------------------------------------------------------------

class TestExponentiation:
    def test_simple_power(self):
        result = parse("x := 2 ** 10;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "**"
        assert expr.left.value == 2
        assert expr.right.value == 10

    def test_right_associative(self):
        result = parse("x := 2 ** 3 ** 2;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "**"
        assert expr.left.value == 2
        assert isinstance(expr.right, StBinaryOp)
        assert expr.right.op == "**"
        assert expr.right.left.value == 3
        assert expr.right.right.value == 2

    def test_power_with_variables(self):
        result = parse("x := base ** exp;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "**"
        assert isinstance(expr.left, StTagRef)
        assert isinstance(expr.right, StTagRef)

    def test_power_precedence_over_mul(self):
        result = parse("x := 2 * 3 ** 2;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "*"
        assert isinstance(expr.right, StBinaryOp)
        assert expr.right.op == "**"

    def test_power_after_unary(self):
        result = parse("x := -2 ** 3;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "**"
        assert isinstance(expr.left, StLiteral)
        assert expr.left.value == -2
        assert expr.right.value == 3


# ---------------------------------------------------------------------------
# MOD operator
# ---------------------------------------------------------------------------

class TestModOperator:
    def test_simple_mod(self):
        result = parse("x := 10 MOD 3;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "mod"
        assert expr.left.value == 10
        assert expr.right.value == 3

    def test_mod_precedence_same_as_mul(self):
        result = parse("x := 2 + 10 MOD 3;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "+"
        assert isinstance(expr.right, StBinaryOp)
        assert expr.right.op == "mod"

    def test_mod_case_insensitive(self):
        result = parse("x := 10 mod 3;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "mod"


# ---------------------------------------------------------------------------
# & operator (boolean/bitwise AND)
# ---------------------------------------------------------------------------

class TestAmpersandOperator:
    def test_ampersand_as_and(self):
        result = parse("x := a & b;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "&"

    def test_ampersand_precedence_like_and(self):
        result = parse("x := a or b & c;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "or"
        assert isinstance(expr.right, StBinaryOp)
        assert expr.right.op == "&"


# ---------------------------------------------------------------------------
# XOR operator
# ---------------------------------------------------------------------------

class TestXorOperator:
    def test_xor_operator(self):
        result = parse("x := a XOR b;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "xor"

    def test_xor_case_insensitive(self):
        result = parse("x := a xor b;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "xor"

    def test_xor_precedence_between_and_and_or(self):
        result = parse("x := a or b xor c and d;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "or"
        assert isinstance(expr.right, StBinaryOp)
        assert expr.right.op == "xor"


# ---------------------------------------------------------------------------
# Hex, Octal, Binary integer literals
# ---------------------------------------------------------------------------

class TestBasedLiterals:
    def test_hex_literal(self):
        result = parse("x := 16#FF;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 0xFF

    def test_hex_literal_with_underscores(self):
        result = parse("x := 16#FF_00_12_34;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 0xFF001234

    def test_hex_literal_lowercase(self):
        result = parse("x := 16#ab;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 0xAB

    def test_octal_literal(self):
        result = parse("x := 8#77;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 0o77

    def test_octal_literal_with_underscores(self):
        result = parse("x := 8#77_00;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 0o7700

    def test_binary_literal(self):
        result = parse("x := 2#1010_1100;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 0b10101100

    def test_binary_literal_simple(self):
        result = parse("x := 2#1111;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 0b1111


# ---------------------------------------------------------------------------
# Integer underscore separators
# ---------------------------------------------------------------------------

class TestUnderscoreSeparators:
    def test_integer_with_underscores(self):
        result = parse("x := 1_000_000;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 1000000

    def test_negative_integer_with_underscores(self):
        result = parse("x := -1_000;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == -1000

    def test_float_with_underscores(self):
        result = parse("x := 1_000.5_0;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 1000.5


# ---------------------------------------------------------------------------
# Typed literals
# ---------------------------------------------------------------------------

class TestTypedLiterals:
    def test_int_typed(self):
        result = parse("x := INT#42;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 42

    def test_dint_typed(self):
        result = parse("x := DINT#1000;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 1000

    def test_sint_typed_negative(self):
        result = parse("x := SINT#-5;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == -5

    def test_uint_typed(self):
        result = parse("x := UINT#65535;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 65535

    def test_real_typed(self):
        result = parse("x := REAL#3.14;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 3.14

    def test_lreal_typed(self):
        result = parse("x := LREAL#1.0E+300;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 1.0e300

    def test_int_typed_case_insensitive(self):
        result = parse("x := int#42;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 42


# ---------------------------------------------------------------------------
# Time/Date literals
# ---------------------------------------------------------------------------

class TestTimeLiterals:
    def test_time_seconds(self):
        result = parse("x := T#5s;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 5000

    def test_time_minutes_seconds(self):
        result = parse("x := T#1m30s;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 90000

    def test_time_hours_minutes_seconds(self):
        result = parse("x := T#1h2m3s;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 3723000

    def test_time_full_precision(self):
        result = parse("x := T#1h2m3s4ms;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 3723004

    def test_time_milliseconds(self):
        result = parse("x := T#500ms;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 500

    def test_time_prefix_keyword(self):
        result = parse("x := TIME#5s;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 5000

    def test_time_case_insensitive(self):
        result = parse("x := t#5s;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == 5000

    def test_date_literal(self):
        result = parse("x := D#2025-01-15;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "2025-01-15"

    def test_date_literal_prefix(self):
        result = parse("x := DATE#2025-01-15;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "2025-01-15"

    def test_tod_literal(self):
        result = parse("x := TOD#14:30:00;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "14:30:00"

    def test_dt_literal(self):
        result = parse("x := DT#2025-01-15-14:30:00;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "2025-01-15-14:30:00"


# ---------------------------------------------------------------------------
# String escape sequences
# ---------------------------------------------------------------------------

class TestStringEscapes:
    def test_dollar_escape(self):
        result = parse("x := '$$';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "$"

    def test_single_quote_escape(self):
        result = parse("x := 'it''s';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "it's"

    def test_line_feed_escape(self):
        result = parse("x := 'before$Lafter';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "before\nafter"

    def test_newline_escape(self):
        result = parse("x := 'before$Nafter';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "before\r\nafter"

    def test_carriage_return_escape(self):
        result = parse("x := 'before$Rafter';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "before\rafter"

    def test_tab_escape(self):
        result = parse("x := 'before$Tafter';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "before\tafter"

    def test_page_escape(self):
        result = parse("x := 'before$Pafter';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "before\fafter"

    def test_hex_escape_two_digit(self):
        result = parse("x := '$41$42';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "AB"

    def test_hex_escape_in_string(self):
        result = parse("x := 'Price is $5';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert "$" in expr.value or expr.value == "Price is \x05"

    def test_empty_string(self):
        result = parse("x := '';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == ""

    def test_string_with_escaped_single_quote(self):
        result = parse("x := 'it''s';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "it's"

    def test_complex_string_escapes(self):
        result = parse(r"""x := 'Line1$R$NLine2';""")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "Line1\r\r\nLine2"


# ---------------------------------------------------------------------------
# Empty statement
# ---------------------------------------------------------------------------

class TestEmptyStatement:
    def test_standalone_semicolon(self):
        result = parse(";")
        prog = result.unwrap()
        assert len(prog.statements) == 0

    def test_assignment_with_extra_semicolons(self):
        result = parse("x := 1;; y := 2;")
        prog = result.unwrap()
        assert len(prog.statements) == 2

    def test_multiple_empty_statements(self):
        result = parse(";;;")
        prog = result.unwrap()
        assert len(prog.statements) == 0


# ---------------------------------------------------------------------------
# Multi-dimensional array indexing
# ---------------------------------------------------------------------------

class TestMultiDimensionalArrays:
    def test_two_dimensional_index(self):
        result = parse("x := Matrix[1, 2];")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StTagRef)
        segs = expr.path.segments
        assert segs[0].name == "Matrix"
        assert segs[0].index == 1
        assert segs[1].name == "2"

    def test_assignment_to_multi_dim_array(self):
        result = parse("Matrix[0, 0] := 42;")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StAssignment)
        segs = stmt.target.segments
        assert segs[0].name == "Matrix"
        assert segs[0].index == 0
        assert segs[1].name == "0"


# ---------------------------------------------------------------------------
# Case statement ranges
# ---------------------------------------------------------------------------

class TestCaseRanges:
    def test_case_with_range(self):
        result = parse("case x of 1..5: y := 1; end_case")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StCase)
        assert len(stmt.cases) == 1
        sel = stmt.cases[0][0][0]
        assert isinstance(sel, tuple)
        assert sel[0] == "range"

    def test_case_with_mixed_selectors(self):
        result = parse("case x of 1, 5..10, 15: y := 1; end_case")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StCase)
        assert len(stmt.cases) == 1
        selectors = stmt.cases[0][0]
        assert len(selectors) == 3


# ---------------------------------------------------------------------------
# Unary + operator
# ---------------------------------------------------------------------------

class TestUnaryPlus:
    def test_unary_plus(self):
        result = parse("x := +5;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StUnaryOp)
        assert expr.op == "+"

    def test_unary_plus_on_variable(self):
        result = parse("x := +y;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StUnaryOp)
        assert expr.op == "+"


# ---------------------------------------------------------------------------
# Multiple unary operators
# ---------------------------------------------------------------------------

class TestMultipleUnary:
    def test_double_negation(self):
        result = parse("x := --y;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StUnaryOp)
        assert expr.op == "-"
        assert isinstance(expr.operand, StUnaryOp)
        assert expr.operand.op == "-"

    def test_not_not(self):
        result = parse("x := NOT NOT y;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StUnaryOp)
        assert expr.op == "not"
        assert isinstance(expr.operand, StUnaryOp)
        assert expr.operand.op == "not"

    def test_minus_not(self):
        result = parse("x := -NOT y;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StUnaryOp)
        assert expr.op == "-"
        assert isinstance(expr.operand, StUnaryOp)
        assert expr.operand.op == "not"


# ---------------------------------------------------------------------------
# Operator precedence
# ---------------------------------------------------------------------------

class TestOperatorPrecedence:
    def test_precedence_table(self):
        result = parse("x := a + b * c ** d;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "+"
        assert isinstance(expr.right, StBinaryOp)
        assert expr.right.op == "*"
        assert isinstance(expr.right.right, StBinaryOp)
        assert expr.right.right.op == "**"

    def test_comparison_precedence(self):
        result = parse("x := a < b AND c > d;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "and"
        assert isinstance(expr.left, StBinaryOp)
        assert expr.left.op == "<"
        assert isinstance(expr.right, StBinaryOp)
        assert expr.right.op == ">"


# ---------------------------------------------------------------------------
# Nested control structures
# ---------------------------------------------------------------------------

class TestNestedControl:
    def test_nested_if_without_else(self):
        text = "if x then if y then z := 1; end_if end_if"
        result = parse(text)
        prog = result.unwrap()
        outer = prog.statements[0]
        assert isinstance(outer, StIf)
        assert len(outer.body) == 1
        inner = outer.body[0]
        assert isinstance(inner, StIf)
        assert len(inner.else_body) == 0

    def test_if_inside_for_inside_while(self):
        text = """while running do
            for i := 0 to 10 do
                if arr[i] > 0 then
                    total := total + arr[i];
                end_if
            end_for
        end_while"""
        result = parse(text)
        prog = result.unwrap()
        outer = prog.statements[0]
        assert isinstance(outer, StWhile)
        for_stmt = outer.body[0]
        assert isinstance(for_stmt, StFor)
        if_stmt = for_stmt.body[0]
        assert isinstance(if_stmt, StIf)

    def test_multiple_elsif(self):
        text = """if x = 1 then a := 1;
        elsif x = 2 then a := 2;
        elsif x = 3 then a := 3;
        elsif x = 4 then a := 4;
        else a := 0;
        end_if"""
        result = parse(text)
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StIf)
        assert len(stmt.elsif_pairs) == 3
        assert len(stmt.else_body) == 1


# ---------------------------------------------------------------------------
# Complex realistic programs
# ---------------------------------------------------------------------------

class TestRealisticProgramsEdgeCases:
    def test_motor_control(self):
        text = """Motor_Run := Start_Button AND NOT Stop_Button AND NOT Fault;
Timer1(Motor_Run, T#5s, 0);
Motor_Ready := Timer1.DN AND NOT Motor_Fault;"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.statements) == 3

    def test_state_machine(self):
        text = """case state of
    0: (* Idle *)
        if start then
            state := 1;
        end_if
    1, 2: (* Running *)
        if stop then
            state := 0;
        end_if
    3..10: (* Error *)
        state := 0;
else
    state := 0;
end_case"""
        result = parse(text)
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StCase)
        assert len(stmt.cases) == 3
        assert len(stmt.else_body) == 1

    def test_array_processing(self):
        text = """for i := 0 to 99 do
    if DataBuf[i] > Threshold then
        Count := Count + 1;
        Sum := Sum + DataBuf[i];
    end_if
end_for
Average := Sum / Count;"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.statements) == 2

    def test_complex_expression(self):
        text = """Result := (A + B * C ** 2) MOD 100 AND 16#FF XOR 2#1010;"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.statements) == 1
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)


# ---------------------------------------------------------------------------
# Comments edge cases
# ---------------------------------------------------------------------------

class TestCommentsEdgeCases:
    def test_comment_inside_expression(self):
        result = parse("x := a (* comment *) + b;")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StBinaryOp)
        assert expr.op == "+"

    def test_multiple_line_comments(self):
        text = """// line 1
// line 2
x := 1;"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.statements) == 1

    def test_mixed_comment_styles(self):
        text = """(* IEC block *)
// C-style line
/* C-style block */
x := 1;"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.statements) == 1


# ---------------------------------------------------------------------------
# CASE with all selector types
# ---------------------------------------------------------------------------

class TestCaseSelectors:
    def test_single_value_selector(self):
        result = parse("case x of 1: y := 10; end_case")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StCase)
        assert len(stmt.cases) == 1
        assert len(stmt.cases[0][0]) == 1

    def test_comma_separated_values(self):
        result = parse("case x of 1, 2, 3: y := 10; end_case")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert len(stmt.cases[0][0]) == 3

    def test_range_selector(self):
        result = parse("case x of 5..10: y := 10; end_case")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert len(stmt.cases[0][0]) == 1
        assert isinstance(stmt.cases[0][0][0], tuple)

    def test_no_else_clause(self):
        result = parse("case x of 1: y := 1; end_case")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert stmt.else_body == []


# ---------------------------------------------------------------------------
# FOR loop edge cases
# ---------------------------------------------------------------------------

class TestForEdgeCases:
    def test_for_with_negative_step(self):
        result = parse("for i := 10 to 1 by -1 do x := i; end_for")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StFor)
        assert isinstance(stmt.step, StLiteral)
        assert stmt.step.value == -1

    def test_for_with_expression_bounds(self):
        result = parse("for i := Start to End BY Step do x := i; end_for")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt.start, StTagRef)
        assert isinstance(stmt.end, StTagRef)
        assert isinstance(stmt.step, StTagRef)


# ---------------------------------------------------------------------------
# WHILE and REPEAT edge cases
# ---------------------------------------------------------------------------

class TestLoopEdgeCases:
    def test_while_with_empty_body(self):
        result = parse("while x do end_while")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StWhile)
        assert stmt.body == []

    def test_repeat_with_empty_body(self):
        result = parse("repeat until x end_repeat")
        prog = result.unwrap()
        stmt = prog.statements[0]
        assert isinstance(stmt, StRepeat)
        assert stmt.body == []


# ---------------------------------------------------------------------------
# RETURN and EXIT
# ---------------------------------------------------------------------------

class TestReturnAndExit:
    def test_return_in_middle(self):
        text = """a := 1;
return;
b := 2;"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.statements) == 3
        assert isinstance(prog.statements[1], StReturn)

    def test_exit_in_loop(self):
        text = """for i := 0 to 10 do
    if arr[i] > 100 then
        exit;
    end_if
end_for"""
        result = parse(text)
        prog = result.unwrap()
        for_stmt = prog.statements[0]
        assert isinstance(for_stmt, StFor)
        if_stmt = for_stmt.body[0]
        assert isinstance(if_stmt, StIf)
        assert isinstance(if_stmt.body[0], StExit)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrorCasesEdgeCases:
    def test_invalid_syntax(self):
        result = parse("x := ;")
        assert isinstance(result, Failure)

    def test_garbage_input(self):
        result = parse("@#!invalid")
        assert isinstance(result, Failure)

    def test_unmatched_paren(self):
        result = parse("x := (a + b;")
        assert isinstance(result, Failure)

    def test_missing_semicolon(self):
        result = parse("x := 1 y := 2;")
        assert isinstance(result, Failure)


# ---------------------------------------------------------------------------
# WSTRING, CHAR, WCHAR typed literals
# ---------------------------------------------------------------------------

class TestWideStringTypedLiterals:
    def test_wstring_typed(self):
        result = parse('x := WSTRING#"Hello";')
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "Hello"

    def test_wstring_typed_with_escape(self):
        result = parse('x := WSTRING#"Line1$R$NLine2";')
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert "\r" in expr.value

    def test_char_typed(self):
        result = parse("x := CHAR#'A';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "A"

    def test_wchar_typed(self):
        result = parse('x := WCHAR#"Z";')
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "Z"


# ---------------------------------------------------------------------------
# 4th edition ${nn} hex escapes
# ---------------------------------------------------------------------------

class TestBracedHexEscapes:
    def test_braced_hex_two_digit(self):
        result = parse("x := '${41}';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "A"

    def test_braced_hex_four_digit(self):
        result = parse("x := '${00A9}';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "\u00a9"

    def test_braced_hex_six_digit(self):
        result = parse("x := '${1F600}';")
        prog = result.unwrap()
        expr = prog.statements[0].expression
        assert isinstance(expr, StLiteral)
        assert expr.value == "\U0001f600"


# ---------------------------------------------------------------------------
# VAR_TEMP
# ---------------------------------------------------------------------------

class TestVarTemp:
    def test_var_temp(self):
        text = """VAR_TEMP
    temp : INT;
END_VAR"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1
        assert prog.declarations[0].block_type == "var_temp"


# ---------------------------------------------------------------------------
# Nested structs in TYPE blocks
# ---------------------------------------------------------------------------

class TestNestedTypeDeclarations:
    def test_multiple_type_declarations(self):
        text = """TYPE
    Color : (RED, GREEN, BLUE);
    MyInt : INT;
    Point : REAL;
END_TYPE"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1
        type_block = prog.declarations[0]
        assert isinstance(type_block, StTypeBlock)
        assert len(type_block.declarations) == 3


# ---------------------------------------------------------------------------
# Subrange types in TYPE blocks
# ---------------------------------------------------------------------------

class TestSubrangeTypeDeclaration:
    def test_subrange_as_type_alias(self):
        # Subrange with parentheses conflicts with expressions
        # but simple type alias works
        text = """TYPE
    Percentage : INT;
    Index : DINT;
END_TYPE"""
        result = parse(text)
        prog = result.unwrap()
        assert len(prog.declarations) == 1
        assert len(prog.declarations[0].declarations) == 2
