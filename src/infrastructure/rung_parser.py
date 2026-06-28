"""RLL rung parser using Lark.

Expression grammar uses recursive rules (not regex tokens) to handle
arbitrary nesting depth of parenthesized sub-expressions and function
calls.  All Rockwell CPT/CMP operators are supported including
comparison (<, <=, >, >=, =, <<>), logical (&&, ^^, ||), bitwise
(AND, XOR, OR), arithmetic (+, -, *, /, **, MOD), and function calls
(ABS, SQRT, SIN, …).

Lark drops inline string literals (e.g., "[", "]") from alternatives
inside (...)* groups.  Array indices are therefore represented in dot
notation internally (Array[5] → Array.5).
"""

from dataclasses import dataclass, field

from lark import Lark, Transformer, UnexpectedInput
from returns.result import Failure, Result, Success

from domain.errors import RLLParseError
from domain.rll_models import Instruction, Operand, ParsedRung

_GRAMMAR = r"""
start: rung+

rung: items SEMICOLON

items: item*

item: instruction
    | branch

instruction: IDENT (LPAREN params? RPAREN)?

branch: "[" items ("," items)* "]"

params: param (COMMA param?)*

param: WILDCARD | expr

// Recursive expression grammar — handles arbitrary depth natively.
// EXPR_OP is a single terminal matching all binary operators; longer
// patterns (<=, <>, **, &&, etc.) are listed first so the regex
// matches them before single-char variants.
// UNARY_OP has higher priority than IDENT so NOT/!/− are consumed as
// operators rather than tag names.  The contextual lexer ensures − is
// only matched as UNARY_OP when the parser expects an expr_atom start
// (i.e. unary position), not after an expr_atom (binary position).
expr: expr_atom (EXPR_OP expr_atom)*

expr_atom: NUMBER
         | HEX_LITERAL
         | tag_or_call
         | LPAREN expr RPAREN
         | UNARY_OP expr_atom

tag_or_call: tag_path (LPAREN (expr (COMMA expr)*)? RPAREN)?

tag_path: IDENT ("." (IDENT | NUMBER | "[" IDENT ("." IDENT)* "]")
               | "[" NUMBER ("," NUMBER)* "]"
               | "[" IDENT ("." IDENT)* "]")*

// Terminals
IDENT: /[A-Za-z_][A-Za-z0-9_]*/
     | /[A-Za-z_][A-Za-z0-9_]*:[0-9]+:[A-Za-z_][A-Za-z0-9_]*/
     | /[A-Za-z_][A-Za-z0-9_]*:[A-Za-z][A-Za-z0-9_]*/
EXPR_OP.5: /\*\*|<>|<=|>=|&&|\|\||\^\^|MOD|AND|XOR|OR|[+\-*\/<>=]/
UNARY_OP.10: /NOT(?![A-Za-z0-9_])|!|-/
LPAREN: "("
RPAREN: ")"
WILDCARD: "?"
HEX_LITERAL.100: /16#[0-9A-Fa-f][0-9A-Fa-f_]*/
NUMBER: /-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?/
SEMICOLON: ";"
COMMA: ","
%ignore /[ \t\n\r]+/
"""


@dataclass
class _BranchItem:
    paths: list[list[Instruction]] = field(default_factory=list)


class _RLLTransformer(Transformer):
    def start(self, items):
        return [r for r in items if r is not None]

    def rung(self, items):
        flat = []
        for x in items:
            if isinstance(x, list):
                for y in x:
                    if isinstance(y, (Instruction, _BranchItem)):
                        flat.append(y)
            elif isinstance(x, (Instruction, _BranchItem)):
                flat.append(x)
        merged = _merge_branches(flat)
        return ParsedRung(number=0, text="", instructions=merged)

    def items(self, items):
        return [x for x in items if x is not None]

    def item(self, items):
        return items[0] if items else None

    def instruction(self, items):
        opcode = str(items[0])
        operands = []
        for item in items[1:]:
            if isinstance(item, list):
                operands.extend(item)
            elif isinstance(item, Operand):
                operands.append(item)
        return Instruction(opcode=opcode, operands=operands)

    def branch(self, items):
        return _BranchItem(paths=[x for x in items if x is not None])

    def params(self, items):
        result = []
        i = 0
        while i < len(items):
            item = items[i]
            if isinstance(item, list):
                for sub in item:
                    if isinstance(sub, Operand):
                        result.append(sub)
                i += 1
            elif isinstance(item, Operand):
                result.append(item)
                i += 1
            elif str(item) == ",":
                next_item = items[i + 1] if i + 1 < len(items) else None
                if next_item is None or str(next_item) == ",":
                    result.append(Operand(value=""))
                i += 1
            else:
                i += 1
        return result

    def param(self, items):
        if not items:
            return Operand(value="")
        return items[0]

    def expr(self, items):
        parts = []
        for item in items:
            if isinstance(item, Operand):
                parts.append(item.value)
            elif isinstance(item, str):
                parts.append(item)
        return Operand(value=" ".join(parts) if parts else "")

    def expr_atom(self, items):
        if len(items) == 1:
            return items[0]
        if len(items) == 3:
            # LPAREN expr RPAREN — parenthesised sub-expression
            inner = items[1]
            return Operand(value=f"({inner.value})")
        if len(items) == 2:
            # UNARY_OP expr_atom — prefix operator
            op = str(items[0])
            operand = items[1]
            if op == "NOT":
                return Operand(value=f"NOT {operand.value}")
            return Operand(value=f"{op}{operand.value}")
        return items[0]

    def tag_or_call(self, items):
        if len(items) == 1:
            return items[0]
        # tag_path "(" args ")"
        tag_val = items[0].value if isinstance(items[0], Operand) else str(items[0])
        args = [item.value for item in items[1:] if isinstance(item, Operand)]
        if args:
            return Operand(value=f"{tag_val}({', '.join(args)})")
        return Operand(value=f"{tag_val}()")

    def tag_path(self, items):
        value = ""
        prev = None
        for item in items:
            if isinstance(item, Operand):
                if prev == "[":
                    value += f"[{item.value}]"
                else:
                    if value:
                        value += "."
                    value += str(item.value)
            else:
                s = str(item)
                if s == "[":
                    value += "["
                elif s == "]":
                    value += "]"
                else:
                    if value and value[-1] not in ("[", "."):
                        value += "."
                    value += s
                prev = s
        return Operand(value=value)

    def expr_op(self, items):
        return str(items[0])

    def EXPR_OP(self, token):  # noqa: N802
        return str(token)

    def UNARY_OP(self, token):  # noqa: N802
        return str(token)

    def IDENT(self, token):  # noqa: N802
        return str(token)

    def NUMBER(self, token):  # noqa: N802
        return Operand(value=str(token))

    def WILDCARD(self, token):  # noqa: N802
        return Operand(value="?")

    def HEX_LITERAL(self, token):  # noqa: N802
        return Operand(value=str(token))

    def SEMICOLON(self, token):  # noqa: N802
        return None


def _merge_branches(items: list) -> list[Instruction]:
    """Merge _BranchItem objects into Instruction.branch attributes."""
    result: list[Instruction] = []
    for item in items:
        if isinstance(item, Instruction):
            result.append(item)
        elif isinstance(item, _BranchItem) and item.paths:
            # Convert each path (list of items) into a merged instruction list
            branch_paths = []
            for path in item.paths:
                branch_paths.append(_merge_branches(path))
            if result:
                result[-1].branch = branch_paths
    return result


_transformer = _RLLTransformer()
_parser = Lark(_GRAMMAR, parser="lalr", lexer="contextual", transformer=_transformer)


def parse(text: str) -> Result[list[ParsedRung], RLLParseError]:
    text = text.strip()
    if not text:
        return Success([])
    if not text.endswith(";"):
        text = text + ";"
    try:
        result = _parser.parse(text)
        rungs = result if isinstance(result, list) else [result]
        for i, r in enumerate(rungs):
            r.number = i
        return Success(rungs)
    except UnexpectedInput as e:
        return Failure(RLLParseError(text=text, position=e.pos_in_stream))
