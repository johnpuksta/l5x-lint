from lark import Lark, Transformer, UnexpectedInput
from returns.result import Failure, Result, Success

from l5x_lint.domain.models import TagPath, TagPathSegment
from l5x_lint.domain.st_models import (
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

_GRAMMAR = r"""
start: st_program
st_program: statement+

statement: assignment
         | if_statement
         | case_statement
         | for_loop
         | while_loop
         | repeat_loop
         | call_statement
         | exit_statement
         | return_statement

assignment: tag_path ASSIGN expression SEMICOLON

if_statement: IF expression THEN statement+ (ELSIF expression THEN statement+)* (ELSE statement+)? END_IF

case_statement: CASE expression OF case_element+ (ELSE statement+)? END_CASE
case_element: expression (COMMA expression)* COLON statement+

for_loop: FOR tag_path ASSIGN expression TO expression (BY expression)? DO statement+ END_FOR

while_loop: WHILE expression DO statement+ END_WHILE

repeat_loop: REPEAT statement+ UNTIL expression END_REPEAT

call_statement: call SEMICOLON

exit_statement: EXIT SEMICOLON

return_statement: RETURN SEMICOLON

call: TAG_BASE LPAREN (expression (COMMA expression)*)? RPAREN
wildcard: WILDCARD

expression: or_expr
or_expr: and_expr (OR and_expr)*
and_expr: compare_expr (AND compare_expr)*
compare_expr: add_expr ((EQ | NE | LT | GT | LE | GE) add_expr)?
add_expr: mul_expr ((PLUS | MINUS) mul_expr)*
mul_expr: unary_expr ((MUL | DIV | MOD) unary_expr)*
unary_expr: (MINUS | NOT)* atom
atom: tag_path | number | bool_literal | wildcard | call | LPAREN expression RPAREN

tag_path: TAG_BASE (DOT TAG_BASE | LSQB INTEGER RSQB)*

number: INTEGER | FLOAT

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
AND: /(?i:and)/
NOT: /(?i:not)/
MOD.100: /(?i:mod)/
TRUE: /(?i:true)/
FALSE: /(?i:false)/

// Operators
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
TAG_BASE.-1: /[A-Za-z_][A-Za-z0-9_]*/
INTEGER: /-?[0-9]+/
FLOAT: /-?[0-9]+\.[0-9]+([eE][-+]?[0-9]+)?/

COMMENT1: /\(\*[\s\S]*?\*\)/
COMMENT2: /\/\/[^\n]*/
%ignore COMMENT1
%ignore COMMENT2
%ignore /[ \t\n\r]+/
"""


class _StTransformer(Transformer):
    def start(self, items):
        return items[0]

    def st_program(self, items):
        return StProgram(statements=list(items))

    def statement(self, items):
        return items[0]

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
        # items: ["case", expr, "of", *case_elements, "end_case"]
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
                # case_element returns (selectors, body_statements)
                cases.append(item)
        return StCase(expression=expr, cases=cases, else_body=else_body)

    def case_element(self, items):
        selectors = items[:-1]
        colon_idx = 0
        for idx, item in enumerate(items):
            if item == ":":
                colon_idx = idx
                break
        selectors = [items[i] for i in range(colon_idx)]
        body = [it for it in items[colon_idx + 1:] if not isinstance(it, str)]
        return (selectors, body)

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

    def exit_statement(self, items):
        return StExit()

    def return_statement(self, items):
        return StReturn()

    def call(self, items):
        name = str(items[0])
        separators = frozenset({",", ")"})
        args = [
            item for item in items[2:]
            if not (isinstance(item, str) and item in separators)
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

    def expression(self, items):
        return items[0]

    def or_expr(self, items):
        return self._build_binary(items, "or")

    def and_expr(self, items):
        return self._build_binary(items, "and")

    def compare_expr(self, items):
        if len(items) == 1:
            return items[0]
        return StBinaryOp(left=items[0], op=items[1], right=items[2])

    def add_expr(self, items):
        return self._build_binary(items, "+", "-")

    def mul_expr(self, items):
        return self._build_binary(items, "*", "/")

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

    def wildcard(self, items):
        return StLiteral(value="?")

    def atom(self, items):
        if len(items) == 3 and str(items[0]) == "(":
            return items[1]
        item = items[0]
        if isinstance(item, TagPath):
            return StTagRef(path=item)
        return item

    def tag_path(self, items):
        segments = [TagPathSegment(name=str(items[0]))]
        for item in items[1:]:
            if isinstance(item, str) and item in {".", "[", "]"}:
                continue
            if isinstance(item, (int, float)):
                segments[-1].index = int(item)
            elif isinstance(item, str) and item.isdigit():
                segments[-1].index = int(item)
            else:
                segments.append(TagPathSegment(name=str(item)))
        return TagPath(segments=segments)

    def number(self, items):
        value = items[0]
        if isinstance(value, float) or "." in str(value):
            return StLiteral(value=float(str(value)))
        return StLiteral(value=int(str(value)))

    def bool_literal(self, items):
        val = str(items[0])
        return StLiteral(value=(val.upper() == "TRUE"))

    def INTEGER(self, token):  # noqa: N802
        return int(str(token))

    def FLOAT(self, token):  # noqa: N802
        return float(str(token))

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

    def AND(self, token):  # noqa: N802
        return "and"

    def NOT(self, token):  # noqa: N802
        return "not"

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

    def LSQB(self, token):  # noqa: N802
        return token.value

    def RSQB(self, token):  # noqa: N802
        return token.value


_transformer = _StTransformer()
_parser = Lark(_GRAMMAR, parser="lalr", transformer=_transformer)


def parse(text: str) -> Result[StProgram, Exception]:
    text = text.strip()
    if not text:
        return Success(StProgram())
    try:
        result = _parser.parse(text)
        return Success(result)
    except UnexpectedInput as e:
        return Failure(e)
