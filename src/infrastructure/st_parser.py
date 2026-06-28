"""ST (Structured Text) parser using Lark.

Lark Scanner Priority:
    TAG_BASE uses priority -1 to sort after keywords (priority 0)
    to prevent identifiers from shadowing keywords.

    All keyword terminals use /(?i:keyword)/ regex (case-insensitive).
    TAG_BASE.-1 ensures identifiers don't match before keywords.

    POWER.200, HEX_LITERAL.100, OCTAL_LITERAL.100, BINARY_LITERAL.100,
    TIME_LITERAL.100, DATE_LITERAL.100, AMPERSAND.100 use high priority
    to match before broader patterns.

IEC 61131-3 Edition 4 Features:
    - Exponentiation ** (right-associative, precedence between unary and *)
    - MOD operator (same precedence as * /)
    - & operator (boolean/bitwise AND, same precedence as AND)
    - Hex (16#FF), Octal (8#77), Binary (2#1010_1100) integer literals
    - Integer underscore separators (1_000_000)
    - Typed literals (INT#42, REAL#3.14, T#5s, D#2025-01-15, etc.)
    - $-based string escape sequences ($$, $', $L, $R, $T, $N, $P, $nn, $nnnn)
    - Empty statements (standalone ;)
    - Multi-dimensional array indexing (Arr[1,2])
"""

import re

from lark import Lark, Transformer, UnexpectedInput
from returns.result import Failure, Result, Success

from domain.errors import STParseError
from domain.models import TagPath, TagPathSegment
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
    StVarDecl,
    StWhile,
)

_GRAMMAR = r"""
start: st_program
st_program: declaration* statement*

declaration: var_block | type_block

type_block: TYPE type_decl+ END_TYPE SEMICOLON?
type_decl: TAG_BASE COLON LPAREN enum_value (COMMA enum_value)* RPAREN SEMICOLON
         | TAG_BASE COLON STRUCT struct_member* END_STRUCT SEMICOLON
         | TAG_BASE COLON TAG_BASE LSQB INTEGER RSQB SEMICOLON
         | TAG_BASE COLON TAG_BASE DOTDOT TAG_BASE SEMICOLON
         | TAG_BASE COLON POINTER TO TAG_BASE SEMICOLON
         | TAG_BASE COLON TAG_BASE SEMICOLON

var_block: var_type var_decl* END_VAR SEMICOLON?
var_type: VAR | VAR_INPUT | VAR_OUTPUT | VAR_IN_OUT | VAR_GLOBAL | VAR_EXTERNAL | VAR_TEMP
var_decl: TAG_BASE COLON type_spec (ASSIGN expression)? (RETAIN | NON_RETAIN | CONSTANT)? SEMICOLON
         | TAG_BASE AT IO_ADDRESS COLON type_spec (ASSIGN expression)? (RETAIN | NON_RETAIN | CONSTANT)? SEMICOLON

type_spec: TAG_BASE
         | TAG_BASE LSQB INTEGER RSQB
         | TAG_BASE LSQB INTEGER COMMA INTEGER RSQB
         | STRUCT struct_member* END_STRUCT
         | ENUM enum_value* END_ENUM
         | TAG_BASE DOTDOT TAG_BASE
         | POINTER TO TAG_BASE

struct_member: TAG_BASE COLON type_spec SEMICOLON
enum_value: TAG_BASE (ASSIGN INTEGER)?

statement: assignment
         | if_statement
         | case_statement
         | for_loop
         | while_loop
         | repeat_loop
         | call_statement
         | exit_statement
         | return_statement
         | empty_statement

assignment: tag_path ASSIGN expression SEMICOLON

if_statement: IF expression THEN statement* (ELSIF expression THEN statement*)* (ELSE statement*)? END_IF SEMICOLON?

case_statement: CASE expression OF case_element+ (ELSE statement*)? END_CASE SEMICOLON?
case_element: case_selector (COMMA case_selector)* COLON statement*
case_selector: expression | expression DOTDOT expression

for_loop: FOR tag_path ASSIGN expression TO expression (BY expression)? DO statement+ END_FOR SEMICOLON?

while_loop: WHILE expression DO statement* END_WHILE SEMICOLON?

repeat_loop: REPEAT statement* UNTIL expression END_REPEAT SEMICOLON?

call_statement: call SEMICOLON

exit_statement: EXIT SEMICOLON

return_statement: RETURN SEMICOLON

empty_statement: SEMICOLON

call: TAG_BASE LPAREN (call_arg (COMMA call_arg)*)? RPAREN
call_arg: expression | TAG_BASE ASSIGN expression
wildcard: WILDCARD

expression: short_circuit_expr
short_circuit_expr: or_expr (AND_THEN or_expr | OR_ELSE or_expr)*
or_expr: xor_expr (OR xor_expr)*
xor_expr: and_expr (XOR and_expr)*
and_expr: compare_expr ((AND | AMPERSAND) compare_expr)*
compare_expr: add_expr ((EQ | NE | LT | GT | LE | GE) add_expr)?
add_expr: mul_expr ((PLUS | MINUS) mul_expr)*
mul_expr: power_expr ((MUL | DIV | MOD) power_expr)*
power_expr: unary_expr (POWER power_expr)?
unary_expr: (MINUS | NOT | PLUS)* atom
atom: tag_path | typed_literal | number | time_literal | date_literal
     | bool_literal | string_literal | wildcard | call | LPAREN expression RPAREN

tag_path: TAG_BASE (DOT TAG_BASE | LSQB expression RSQB | LSQB expression (COMMA expression)* RSQB)*

typed_literal: INT_TYPED | DINT_TYPED | SINT_TYPED | UINT_TYPED
             | REAL_TYPED | LREAL_TYPED | TIME_TYPED | DATE_TYPED
             | TOD_TYPED | DT_TYPED | STRING_TYPED | WSTRING_TYPED
             | CHAR_TYPED | WCHAR_TYPED

time_literal: TIME_LITERAL
date_literal: DATE_LITERAL | TOD_LITERAL | DT_LITERAL

number: INTEGER | HEX_LITERAL | OCTAL_LITERAL | BINARY_LITERAL | FLOAT

string_literal: STRING

bool_literal: TRUE | FALSE

// Keywords — case-insensitive via inline regex flag
IF: /(?i:if)/
THEN: /(?i:then)/
ELSIF: /(?i:elsif)/
ELSE: /(?i:else)/
END_IF: /(?i:end_if)/
CASE: /(?i:case)/
OF: /(?i:of)/
END_CASE: /(?i:end_case)/
FOR: /(?i:for)/
TO: /(?i:to)/
BY: /(?i:by)/
DO: /(?i:do)/
END_FOR: /(?i:end_for)/
WHILE: /(?i:while)/
END_WHILE: /(?i:end_while)/
REPEAT: /(?i:repeat)/
UNTIL: /(?i:until)/
END_REPEAT: /(?i:end_repeat)/
EXIT: /(?i:exit)/
RETURN: /(?i:return)/
OR: /(?i:or)/
OR_ELSE.100: /(?i:or_else)/
AND: /(?i:and)/
AND_THEN.100: /(?i:and_then)/
XOR: /(?i:xor)/
NOT: /(?i:not)/
MOD.100: /(?i:mod)/
TRUE: /(?i:true)/
FALSE: /(?i:false)/
TYPE.100: /(?i:type)/
END_TYPE.100: /(?i:end_type)/
STRUCT.100: /(?i:struct)/
END_STRUCT.100: /(?i:end_struct)/
ENUM.100: /(?i:enum)/
END_ENUM.100: /(?i:end_enum)/
POINTER.100: /(?i:pointer)/
AT.100: /(?i:at)/
VAR.100: /(?i:var)(?![\w])/
VAR_INPUT.100: /(?i:var_input)/
VAR_OUTPUT.100: /(?i:var_output)/
VAR_IN_OUT.100: /(?i:var_in_out)/
VAR_GLOBAL.100: /(?i:var_global)/
VAR_EXTERNAL.100: /(?i:var_external)/
VAR_TEMP.100: /(?i:var_temp)/
END_VAR.100: /(?i:end_var)/
RETAIN.100: /(?i:retain)/
NON_RETAIN.100: /(?i:non_retain)/
CONSTANT.100: /(?i:constant)/

// Operators
POWER.200: "**"
ASSIGN: ":="
EQ: "="
NE: "<>"
LE: "<="
GE: ">="
LT: "<"
GT: ">"
PLUS: "+"
MINUS: "-"
MUL: "*"
DIV: "/"
AMPERSAND.100: "&"
DOTDOT: ".."

// Structure
LPAREN: "("
RPAREN: ")"
COMMA: ","
COLON: ":"
SEMICOLON: ";"
DOT: "."
LSQB: "["
RSQB: "]"

// Identifiers and literals
WILDCARD: "?"
IO_ADDRESS.100: /%[IQM][XBWDL][0-9]+(\.[0-9]+)?/
TAG_BASE.-1: /[A-Za-z_][A-Za-z0-9_]*/

// Numeric literals — hex, octal, binary with optional underscore separators
HEX_LITERAL.100: /16#[0-9A-Fa-f][0-9A-Fa-f_]*/ | /16#[0-9A-Fa-f][0-9A-Fa-f_]*\.[0-9A-Fa-f][0-9A-Fa-f_]*/
OCTAL_LITERAL.100: /8#[0-7][0-7_]*/
BINARY_LITERAL.100: /2#[01][01_]*/
INTEGER: /-?[0-9][0-9_]*/
FLOAT: /-?[0-9][0-9_]*\.[0-9][0-9_]*([eE][-+]?[0-9][0-9_]*)?/

// Typed literals — INT#42, REAL#3.14, T#5s, D#2025-01-15, etc.
INT_TYPED.100: /(?i:int)#-?[0-9][0-9_]*/
DINT_TYPED.100: /(?i:dint)#-?[0-9][0-9_]*/
SINT_TYPED.100: /(?i:sint)#-?[0-9][0-9_]*/
UINT_TYPED.100: /(?i:uint)#[0-9][0-9_]*/
REAL_TYPED.100: /(?i:real)#-?[0-9][0-9_]*\.[0-9][0-9_]*/
LREAL_TYPED.100: /(?i:lreal)#-?[0-9][0-9_]*\.[0-9][0-9_]*([eE][-+]?[0-9][0-9_]*)?/
TIME_TYPED.100: /(?i:time)#-?[0-9]+(d|h|m(?!s)|s|ms|us|ns)/
DATE_TYPED.100: /(?i:date)#[0-9]{4}-[0-9]{2}-[0-9]{2}/
TOD_TYPED.100: /(?i:(?:time_of_day|tod))#[0-9]{2}:[0-9]{2}:[0-9]{2}/
DT_TYPED.100: /(?i:(?:date_and_time|dt))#[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}:[0-9]{2}:[0-9]{2}/
STRING_TYPED.100: /(?i:string)(?:\([0-9]+\))?#'[^']*(?:''[^']*)*'/
WSTRING_TYPED.100: /(?i:wstring)(?:\([0-9]+\))?#"[^"]*(?:""[^"]*)*"/
CHAR_TYPED.100: /(?i:char)#'[^']'/
WCHAR_TYPED.100: /(?i:wchar)#"[^"]"/

// Time literal — T#5s, T#1h2m3s4ms, TIME#5s
// Longest patterns first to avoid premature short matches
TIME_LITERAL.100: /(?i:t(?:ime)?)#[0-9]+d[0-9]+h[0-9]+m(?!s)[0-9]+s[0-9]+ms[0-9]+us[0-9]+ns/
              | /(?i:t(?:ime)?)#[0-9]+d[0-9]+h[0-9]+m(?!s)[0-9]+s[0-9]+ms/
              | /(?i:t(?:ime)?)#[0-9]+d[0-9]+h[0-9]+m(?!s)[0-9]+s/
              | /(?i:t(?:ime)?)#[0-9]+h[0-9]+m(?!s)[0-9]+s[0-9]+ms/
              | /(?i:t(?:ime)?)#[0-9]+h[0-9]+m(?!s)[0-9]+s/
              | /(?i:t(?:ime)?)#[0-9]+m(?!s)[0-9]+s[0-9]+ms/
              | /(?i:t(?:ime)?)#[0-9]+d[0-9]+h[0-9]+m(?!s)/
              | /(?i:t(?:ime)?)#[0-9]+d[0-9]+h/
              | /(?i:t(?:ime)?)#[0-9]+h[0-9]+m(?!s)/
              | /(?i:t(?:ime)?)#[0-9]+m(?!s)[0-9]+s/
              | /(?i:t(?:ime)?)#[0-9]+s[0-9]+ms/
              | /(?i:t(?:ime)?)#[0-9]+d/
              | /(?i:t(?:ime)?)#[0-9]+h/
              | /(?i:t(?:ime)?)#[0-9]+m(?!s)/
              | /(?i:t(?:ime)?)#[0-9]+s/
              | /(?i:t(?:ime)?)#[0-9]+ms/
              | /(?i:t(?:ime)?)#[0-9]+us/
              | /(?i:t(?:ime)?)#[0-9]+ns/

// Date/time literals — D#2025-01-15, TOD#14:30:00, DT#2025-01-15-14:30:00
DATE_LITERAL.100: /(?i:d(?:ate)?)#[0-9]{4}-[0-9]{2}-[0-9]{2}/
TOD_LITERAL.100: /(?i:(?:time_of_day|tod))#[0-9]{2}:[0-9]{2}:[0-9]{2}/
DT_LITERAL.100: /(?i:(?:date_and_time|dt))#[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}:[0-9]{2}:[0-9]{2}/

// String — single-quoted with '' escape
STRING: /'[^']*(?:''[^']*)*'/

// Comments
COMMENT1: /\(\*[\s\S]*?\*\)/
COMMENT2: /\/\/[^\n]*/
COMMENT3: /\/\*[\s\S]*?\*\//
REGION: /(?i:#region[^\n]*)/
ENDREGION: /(?i:#endregion[^\n]*)/
%ignore COMMENT1
%ignore COMMENT2
%ignore COMMENT3
%ignore REGION
%ignore ENDREGION
%ignore /[ \t\n\r]+/
"""


def _process_string_escapes(s: str) -> str:
    """Process IEC 61131-3 $-based string escape sequences.

    Supports both 2nd edition ($nn) and 4th edition (${nn}) hex escapes.
    """
    result = []
    i = 0
    while i < len(s):
        if s[i] == "$" and i + 1 < len(s):
            next_char = s[i + 1]
            if next_char == "$":
                result.append("$")
                i += 2
            elif next_char in ("'", '"'):
                result.append(next_char)
                i += 2
            elif next_char in ("L", "l"):
                result.append("\n")
                i += 2
            elif next_char in ("N", "n"):
                result.append("\r\n")
                i += 2
            elif next_char in ("R", "r"):
                result.append("\r")
                i += 2
            elif next_char in ("T", "t"):
                result.append("\t")
                i += 2
            elif next_char in ("P", "p"):
                result.append("\f")
                i += 2
            elif next_char == "{":
                # 4th edition braced hex: ${nn}, ${nnnn}, ${nnnnnn}
                j = i + 2
                while j < len(s) and s[j] != "}" and j < i + 10:
                    j += 1
                if j < len(s) and s[j] == "}":
                    hex_str = s[i + 2 : j]
                    try:
                        result.append(chr(int(hex_str, 16)))
                    except ValueError:
                        result.append(s[i : j + 1])
                    i = j + 1
                else:
                    result.append(s[i])
                    i += 1
            elif next_char in "0123456789ABCDEFabcdef":
                # Hex escape: $nn (2 hex digits for STRING, up to 4 for WSTRING)
                hex_str = ""
                j = i + 1
                while j < len(s) and j < i + 5 and s[j] in "0123456789ABCDEFabcdef":
                    hex_str += s[j]
                    j += 1
                if hex_str:
                    try:
                        result.append(chr(int(hex_str, 16)))
                    except ValueError:
                        result.append("$" + hex_str)
                    i = j
                else:
                    result.append(s[i])
                    i += 1
            else:
                result.append(s[i])
                i += 1
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


def _parse_int_literal(text: str) -> int:
    """Parse an integer literal, stripping underscores."""
    return int(text.replace("_", ""))


def _parse_float_literal(text: str) -> float:
    """Parse a float literal, stripping underscores."""
    return float(text.replace("_", ""))


def _parse_based_literal(text: str) -> int:
    """Parse a based literal like 16#FF, 8#77, 2#1010_1100."""
    base_str, value_str = text.split("#", 1)
    base = int(base_str)
    return int(value_str.replace("_", ""), base)


def _parse_time_literal(text: str) -> int:
    """Parse a time literal like T#5s, T#1h2m3s4ms into milliseconds."""
    # Strip the prefix (T# or TIME#)
    _, value = text.split("#", 1)
    value = value.lower()

    total_ms = 0
    # Parse each component
    pattern = re.compile(r"(\d+)(d|h|m(?!s)|s|ms|us|ns)")
    for match in pattern.finditer(value):
        num = int(match.group(1))
        unit = match.group(2)
        if unit == "d":
            total_ms += num * 86400000
        elif unit == "h":
            total_ms += num * 3600000
        elif unit == "m":
            total_ms += num * 60000
        elif unit == "s":
            total_ms += num * 1000
        elif unit == "ms":
            total_ms += num
        elif unit == "us":
            total_ms += num // 1000
        elif unit == "ns":
            total_ms += num // 1000000
    return total_ms


def _parse_date_literal(text: str) -> str:
    """Parse a date literal like D#2025-01-15."""
    _, value = text.split("#", 1)
    return value.strip()


class _StTransformer(Transformer):
    def start(self, items):
        return items[0]

    def st_program(self, items):
        declarations = []
        statements = []
        for item in items:
            if item is None:
                continue
            if isinstance(item, (StVarBlock, StTypeBlock)):
                declarations.append(item)
            else:
                statements.append(item)
        return StProgram(declarations=declarations, statements=statements)

    def declaration(self, items):
        return items[0] if items else None

    def var_type(self, items):
        return str(items[0]).lower()

    def var_block(self, items):
        block_type = str(items[0]).lower()
        decls = [d for d in items[1:] if isinstance(d, StVarDecl)]
        return StVarBlock(block_type=block_type, declarations=decls)

    def var_decl(self, items):
        name = str(items[0])
        type_name = ""
        dimension = 0
        at_address = ""
        initial_value = None
        retain = False
        non_retain = False
        constant = False
        i = 1
        # Check for AT address
        if isinstance(items[i], str) and items[i] == "at":
            at_address = str(items[i + 1])
            i += 3  # skip AT, address, COLON
        # Skip COLON
        if isinstance(items[i], str) and items[i] == ":":
            i += 1
        # type_spec returns (type_name, dimension) tuple
        if isinstance(items[i], tuple):
            type_name, dimension = items[i]
        else:
            type_name = str(items[i])
        i += 1
        # Check for ASSIGN expression
        if i < len(items) and isinstance(items[i], str) and items[i] == ":=":
            initial_value = items[i + 1]
            i += 2
        # Check for qualifiers
        for j in range(i, len(items)):
            val = items[j] if isinstance(items[j], str) else str(items[j])
            val = val.lower()
            if val == "retain":
                retain = True
            elif val == "non_retain":
                non_retain = True
            elif val == "constant":
                constant = True
        return StVarDecl(
            name=name,
            type_name=type_name,
            dimension=dimension,
            at_address=at_address,
            initial_value=initial_value,
            retain=retain,
            non_retain=non_retain,
            constant=constant,
        )

    def type_block(self, items):
        decls = [d for d in items[1:] if d is not None and not isinstance(d, str)]
        return StTypeBlock(declarations=decls)

    def type_decl(self, items):
        # items: [name, ":", ...type_def..., ";"]
        name = str(items[0])
        # Find the type definition (skip ":", "(", etc.)
        type_def = []
        for item in items[2:]:
            if isinstance(item, str) and item == ";":
                break
            if isinstance(item, str) and item in (":", "(", ")", "pointer", "to", ","):
                continue
            type_def.append(item)
        return (name, type_def)

    def struct_member(self, items):
        return ("member", str(items[0]), str(items[2]) if len(items) > 2 else "")

    def enum_value(self, items):
        name = str(items[0])
        value = int(str(items[2])) if len(items) > 2 and items[2] is not None else None
        return (name, value)

    def type_spec(self, items):
        # Returns (type_name, dimension) tuple
        type_name = str(items[0])
        dimension = 0
        if len(items) > 1:
            # Check for [N] dimension
            for i, item in enumerate(items):
                if isinstance(item, str) and item == "[" and i + 1 < len(items):
                    try:
                        dimension = int(str(items[i + 1]))
                    except (ValueError, TypeError):
                        pass
        return (type_name, dimension)

    def io_address(self, token):  # noqa: N802
        return str(token)

    def statement(self, items):
        return items[0]

    def empty_statement(self, _items):
        return None

    def assignment(self, items):
        target, _assign, expr, _semi = items
        return StAssignment(target=target, expression=expr)

    def if_statement(self, items):
        cond = items[1]
        body = []
        elsif_pairs = []
        else_body = []
        i = 3
        while i < len(items) and not isinstance(items[i], str):
            body.append(items[i])
            i += 1
        while i < len(items):
            marker = items[i]
            i += 1
            if marker == "elsif":
                elsif_cond = items[i]
                i += 2
                elsif_body = []
                while i < len(items) and not isinstance(items[i], str):
                    elsif_body.append(items[i])
                    i += 1
                elsif_pairs.append((elsif_cond, elsif_body))
            elif marker == "else":
                while i < len(items) and not isinstance(items[i], str):
                    else_body.append(items[i])
                    i += 1
            elif marker == "end_if":
                break
        return StIf(
            condition=cond,
            body=body,
            elsif_pairs=elsif_pairs,
            else_body=else_body,
        )

    def case_statement(self, items):
        expr = items[1]
        cases = []
        else_body = []
        i = 3
        while i < len(items):
            item = items[i]
            i += 1
            if item == "else":
                while i < len(items) and items[i] != "end_case":
                    else_body.append(items[i])
                    i += 1
            elif item == "end_case":
                break
            else:
                cases.append(item)
        return StCase(expression=expr, cases=cases, else_body=else_body)

    def case_element(self, items):
        # items: [selector, ",", selector, ..., ":", statement*]
        selectors = []
        body = []
        in_body = False
        for item in items:
            if item == ":":
                in_body = True
                continue
            if in_body:
                if not isinstance(item, str):
                    body.append(item)
            else:
                if not isinstance(item, str) or item != ",":
                    selectors.append(item)
        return (selectors, body)

    def case_selector(self, items):
        if len(items) == 1:
            return items[0]
        # Range: expression DOTDOT expression
        return ("range", items[0], items[2])

    def for_loop(self, items):
        var = items[1]
        start = items[3]
        end = items[5]
        step = None
        body_start = 6
        if body_start < len(items) and items[body_start] == "by":
            step = items[body_start + 1]
            body_start += 2
        body_start += 1
        body = [it for it in items[body_start:] if not isinstance(it, str)]
        return StFor(variable=var, start=start, end=end, step=step, body=body)

    def while_loop(self, items):
        cond = items[1]
        body = [it for it in items[3:] if not isinstance(it, str)]
        return StWhile(condition=cond, body=body)

    def repeat_loop(self, items):
        until_idx = 0
        for idx, item in enumerate(items):
            if item == "until":
                until_idx = idx
                break
        body = [items[i] for i in range(1, until_idx) if not isinstance(items[i], str)]
        until = items[until_idx + 1]
        return StRepeat(body=body, until=until)

    def call_statement(self, items):
        callee, _semi = items
        return callee

    def exit_statement(self, _items):
        return StExit()

    def return_statement(self, _items):
        return StReturn()

    def call(self, items):
        name = str(items[0])
        # Filter out separators
        args = [
            item
            for item in items[2:]
            if not (isinstance(item, str) and item in {",", ")"})
        ]
        if name.lower() == "jsr":
            routine_name = ""
            rest_args = args
            if args:
                first = args[0]
                if isinstance(first, StTagRef):
                    routine_name = first.path.segments[0].name
                else:
                    routine_name = str(first)
                rest_args = args[1:]
            return StJsr(routine_name=routine_name, args=rest_args)
        return StCall(name=name, args=args)

    def call_arg(self, items):
        if len(items) == 1:
            return items[0]
        # Named parameter: TAG_BASE ASSIGN expression
        name = str(items[0])
        value = items[2] if len(items) > 2 else items[1]
        return StNamedArg(name=name, value=value)

    def expression(self, items):
        return items[0]

    def short_circuit_expr(self, items):
        return self._build_binary(items, "and_then", "or_else")

    def or_expr(self, items):
        return self._build_binary(items, "or")

    def xor_expr(self, items):
        return self._build_binary(items, "xor")

    def and_expr(self, items):
        return self._build_binary(items, "and", "&")

    def compare_expr(self, items):
        if len(items) == 1:
            return items[0]
        return StBinaryOp(left=items[0], op=items[1], right=items[2])

    def add_expr(self, items):
        return self._build_binary(items, "+", "-")

    def mul_expr(self, items):
        return self._build_binary(items, "*", "/", "mod")

    def power_expr(self, items):
        if len(items) == 1:
            return items[0]
        # Right-associative: a ** b ** c = a ** (b ** c)
        result = items[0]
        i = 1
        while i < len(items):
            right = items[i + 1] if i + 1 < len(items) else items[i]
            i += 2
            result = StBinaryOp(left=result, op="**", right=right)
        return result

    def _build_binary(self, items, *ops):
        if len(items) == 1:
            return items[0]
        result = items[0]
        i = 1
        while i < len(items):
            op = items[i]
            i += 1
            right = items[i]
            i += 1
            result = StBinaryOp(left=result, op=op, right=right)
        return result

    def unary_expr(self, items):
        result = items[-1]
        for item in reversed(items[:-1]):
            result = StUnaryOp(op=item, operand=result)
        return result

    def wildcard(self, _items):
        return StLiteral(value="?")

    def atom(self, items):
        if len(items) == 3 and str(items[0]) == "(":
            return items[1]
        item = items[0]
        if isinstance(item, TagPath):
            return StTagRef(path=item)
        return item

    def typed_literal(self, items):
        raw = str(items[0])
        if "#" not in raw:
            return StLiteral(value=raw)
        type_prefix, value_str = raw.split("#", 1)
        type_lower = type_prefix.lower()
        if type_lower in ("int", "dint", "sint", "uint", "lint", "udint", "usint", "ulint"):
            return StLiteral(value=_parse_int_literal(value_str))
        elif type_lower in ("real", "lreal"):
            return StLiteral(value=_parse_float_literal(value_str))
        elif type_lower in ("time",):
            return StLiteral(value=_parse_time_literal(raw))
        elif type_lower in ("date",):
            return StLiteral(value=_parse_date_literal(raw))
        elif type_lower in ("tod", "time_of_day"):
            return StLiteral(value=_parse_date_literal(raw))
        elif type_lower in ("dt", "date_and_time"):
            return StLiteral(value=_parse_date_literal(raw))
        elif type_lower in ("string",):
            inner = value_str[1:-1] if len(value_str) >= 2 else value_str
            return StLiteral(value=_process_string_escapes(inner.replace("''", "'")))
        elif type_lower in ("wstring",):
            inner = value_str[1:-1] if len(value_str) >= 2 else value_str
            return StLiteral(value=_process_string_escapes(inner.replace('""', '"')))
        elif type_lower in ("char",):
            return StLiteral(value=value_str[1] if len(value_str) >= 2 else "")
        elif type_lower in ("wchar",):
            return StLiteral(value=value_str[1] if len(value_str) >= 2 else "")
        return StLiteral(value=raw)

    def time_literal(self, items):
        return StLiteral(value=_parse_time_literal(str(items[0])))

    def date_literal(self, items):
        return StLiteral(value=_parse_date_literal(str(items[0])))

    def tag_path(self, items):
        segments = [TagPathSegment(name=str(items[0]))]
        for item in items[1:]:
            if isinstance(item, str) and item in {".", "[", "]", ","}:
                continue
            # StLiteral with integer value → array index
            if isinstance(item, StLiteral) and isinstance(item.value, int):
                if segments[-1].index is not None:
                    segments.append(TagPathSegment(name=str(item.value)))
                else:
                    segments[-1].index = item.value
            # StTagRef used as array index (variable index) → treat as name segment
            elif isinstance(item, StTagRef):
                segments.append(TagPathSegment(name=item.path.segments[0].name))
            elif isinstance(item, (int, float)):
                if segments[-1].index is not None:
                    segments.append(TagPathSegment(name=str(int(item))))
                else:
                    segments[-1].index = int(item)
            elif isinstance(item, str) and item.isdigit():
                if segments[-1].index is not None:
                    segments.append(TagPathSegment(name=item))
                else:
                    segments[-1].index = int(item)
            elif isinstance(item, str):
                segments.append(TagPathSegment(name=str(item)))
        return TagPath(segments=segments)

    def string_literal(self, items):
        raw = str(items[0])
        inner = raw[1:-1].replace("''", "'")
        return StLiteral(value=_process_string_escapes(inner))

    def number(self, items):
        value = items[0]
        if isinstance(value, float):
            return StLiteral(value=value)
        if isinstance(value, int):
            return StLiteral(value=value)
        s = str(value)
        if s.startswith("16#") or s.startswith("8#") or s.startswith("2#"):
            return StLiteral(value=_parse_based_literal(s))
        if "." in s or "e" in s.lower():
            return StLiteral(value=_parse_float_literal(s))
        return StLiteral(value=_parse_int_literal(s))

    def bool_literal(self, items):
        val = str(items[0])
        return StLiteral(value=(val.upper() == "TRUE"))

    def INTEGER(self, token):  # noqa: N802
        return int(str(token).replace("_", ""))

    def FLOAT(self, token):  # noqa: N802
        return float(str(token).replace("_", ""))

    def HEX_LITERAL(self, token):  # noqa: N802
        return str(token)

    def OCTAL_LITERAL(self, token):  # noqa: N802
        return str(token)

    def BINARY_LITERAL(self, token):  # noqa: N802
        return str(token)

    def TIMELiteral(self, token):  # noqa: N802
        return str(token)

    def DATELiteral(self, token):  # noqa: N802
        return str(token)

    def TODLiteral(self, token):  # noqa: N802
        return str(token)

    def DTLiteral(self, token):  # noqa: N802
        return str(token)

    def INT_TYPED(self, token):  # noqa: N802
        return str(token)

    def DINT_TYPED(self, token):  # noqa: N802
        return str(token)

    def SINT_TYPED(self, token):  # noqa: N802
        return str(token)

    def UINT_TYPED(self, token):  # noqa: N802
        return str(token)

    def REAL_TYPED(self, token):  # noqa: N802
        return str(token)

    def LREAL_TYPED(self, token):  # noqa: N802
        return str(token)

    def TIME_TYPED(self, token):  # noqa: N802
        return str(token)

    def DATE_TYPED(self, token):  # noqa: N802
        return str(token)

    def TOD_TYPED(self, token):  # noqa: N802
        return str(token)

    def DT_TYPED(self, token):  # noqa: N802
        return str(token)

    def STRING_TYPED(self, token):  # noqa: N802
        return str(token)

    def WSTRING_TYPED(self, token):  # noqa: N802
        return str(token)

    def CHAR_TYPED(self, token):  # noqa: N802
        return str(token)

    def WCHAR_TYPED(self, token):  # noqa: N802
        return str(token)

    def TRUE(self, token):  # noqa: N802
        return str(token)

    def FALSE(self, token):  # noqa: N802
        return str(token)

    def TAG_BASE(self, token):  # noqa: N802
        return str(token)

    def WILDCARD(self, token):  # noqa: N802
        return str(token)

    def OR(self, token):  # noqa: N802
        return "or"

    def OR_ELSE(self, token):  # noqa: N802
        return "or_else"

    def AND(self, token):  # noqa: N802
        return "and"

    def AND_THEN(self, token):  # noqa: N802
        return "and_then"

    def XOR(self, token):  # noqa: N802
        return "xor"

    def NOT(self, token):  # noqa: N802
        return "not"

    def AMPERSAND(self, token):  # noqa: N802
        return "&"

    def POWER(self, token):  # noqa: N802
        return "**"

    def EQ(self, token):  # noqa: N802
        return "="

    def NE(self, token):  # noqa: N802
        return "<>"

    def LE(self, token):  # noqa: N802
        return "<="

    def GE(self, token):  # noqa: N802
        return ">="

    def LT(self, token):  # noqa: N802
        return "<"

    def GT(self, token):  # noqa: N802
        return ">"

    def PLUS(self, token):  # noqa: N802
        return "+"

    def MINUS(self, token):  # noqa: N802
        return "-"

    def MUL(self, token):  # noqa: N802
        return "*"

    def DIV(self, token):  # noqa: N802
        return "/"

    def MOD(self, token):  # noqa: N802
        return "mod"

    def ASSIGN(self, token):  # noqa: N802
        return token.value

    def IF(self, token):  # noqa: N802
        return "if"

    def THEN(self, token):  # noqa: N802
        return "then"

    def ELSIF(self, token):  # noqa: N802
        return "elsif"

    def ELSE(self, token):  # noqa: N802
        return "else"

    def END_IF(self, token):  # noqa: N802
        return "end_if"

    def CASE(self, token):  # noqa: N802
        return "case"

    def OF(self, token):  # noqa: N802
        return "of"

    def END_CASE(self, token):  # noqa: N802
        return "end_case"

    def FOR(self, token):  # noqa: N802
        return "for"

    def TO(self, token):  # noqa: N802
        return "to"

    def BY(self, token):  # noqa: N802
        return "by"

    def DO(self, token):  # noqa: N802
        return "do"

    def END_FOR(self, token):  # noqa: N802
        return "end_for"

    def WHILE(self, token):  # noqa: N802
        return "while"

    def END_WHILE(self, token):  # noqa: N802
        return "end_while"

    def REPEAT(self, token):  # noqa: N802
        return "repeat"

    def UNTIL(self, token):  # noqa: N802
        return "until"

    def END_REPEAT(self, token):  # noqa: N802
        return "end_repeat"

    def EXIT(self, token):  # noqa: N802
        return "exit"

    def RETURN(self, token):  # noqa: N802
        return "return"

    def TYPE(self, token):  # noqa: N802
        return "type"

    def END_TYPE(self, token):  # noqa: N802
        return "end_type"

    def STRUCT(self, token):  # noqa: N802
        return "struct"

    def END_STRUCT(self, token):  # noqa: N802
        return "end_struct"

    def ENUM(self, token):  # noqa: N802
        return "enum"

    def END_ENUM(self, token):  # noqa: N802
        return "end_enum"

    def POINTER(self, token):  # noqa: N802
        return "pointer"

    def AT(self, token):  # noqa: N802
        return "at"

    def VAR(self, token):  # noqa: N802
        return "var"

    def VAR_INPUT(self, token):  # noqa: N802
        return "var_input"

    def VAR_OUTPUT(self, token):  # noqa: N802
        return "var_output"

    def VAR_IN_OUT(self, token):  # noqa: N802
        return "var_in_out"

    def VAR_GLOBAL(self, token):  # noqa: N802
        return "var_global"

    def VAR_EXTERNAL(self, token):  # noqa: N802
        return "var_external"

    def VAR_TEMP(self, token):  # noqa: N802
        return "var_temp"

    def END_VAR(self, token):  # noqa: N802
        return "end_var"

    def RETAIN(self, token):  # noqa: N802
        return "retain"

    def NON_RETAIN(self, token):  # noqa: N802
        return "non_retain"

    def CONSTANT(self, token):  # noqa: N802
        return "constant"

    def IO_ADDRESS(self, token):  # noqa: N802
        return str(token)

    def SEMICOLON(self, token):  # noqa: N802
        return token.value

    def LPAREN(self, token):  # noqa: N802
        return token.value

    def RPAREN(self, token):  # noqa: N802
        return token.value

    def COMMA(self, token):  # noqa: N802
        return token.value

    def COLON(self, token):  # noqa: N802
        return token.value

    def DOT(self, token):  # noqa: N802
        return token.value

    def DOTDOT(self, token):  # noqa: N802
        return token.value

    def LSQB(self, token):  # noqa: N802
        return token.value

    def RSQB(self, token):  # noqa: N802
        return token.value


_transformer = _StTransformer()
_parser = Lark(_GRAMMAR, parser="lalr", transformer=_transformer)


def parse(text: str) -> Result[StProgram, STParseError]:
    text = text.strip()
    if not text:
        return Success(StProgram())
    try:
        result = _parser.parse(text)
        return Success(result)
    except UnexpectedInput as e:
        return Failure(STParseError(text=text, position=e.pos_in_stream))
