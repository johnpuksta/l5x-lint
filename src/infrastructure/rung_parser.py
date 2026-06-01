"""RLL rung parser using Lark.

Lark Scanner Priority:
    Lark's BasicLexer._build_scanner() sorts terminals by
    (-priority, -max_width, -len(pattern.value), name) ascending.
    Higher numeric priority in grammar (e.g., NAME.100) means the
    terminal matches first (because -100 < 0).

    TAG_BASE uses priority -1 to sort after keywords (priority 0)
    — otherwise -max_width tiebreaker puts unbounded TAG_BASE before
    fixed-length keywords like IF.

    CMP.100 and HEX_LITERAL.100 use high priority to match before
    broader OPCODE/NUMBER patterns.

Inline String Literals in Alternatives:
    Lark drops inline string literal tokens (e.g., "[", "]") from
    alternatives within (...)* groups. The tag_path rule uses
    "[" NUMBER ("," NUMBER)* "]" but the transformer receives only
    TAG_BASE, NUMBER tokens — brackets are invisible. Array indices
    are internally represented as .N (dot notation). To preserve
    brackets, use named terminals (LSQB: "[", RSQB: "]") in grammar.
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

instruction: CMP "(" CMP_CONTENT ")"
           | OPCODE ("(" params? ")")?

branch: "[" items ("," items)* "]"

params: param ("," param)*

param: tag_path
     | NUMBER
     | HEX_LITERAL
     | WILDCARD
     | EXPR

tag_path: TAG_BASE ("." (TAG_BASE | NUMBER | "[" TAG_BASE ("." TAG_BASE)* "]") | "[" NUMBER ("," NUMBER)* "]" | "[" TAG_BASE ("." TAG_BASE)* "]")*

// Tokens
OPCODE: /[A-Za-z_][A-Za-z0-9_]*/
TAG_BASE: /[A-Za-z_][A-Za-z0-9_]*:[0-9]+:[A-Za-z_][A-Za-z0-9_]*/
        | /[A-Za-z_][A-Za-z0-9_]*/
WILDCARD: "?"
HEX_LITERAL.100: /[0-9]+#[0-9A-Fa-f]+/
NUMBER: /-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?/
SEMICOLON: ";"
EXPR: /[A-Za-z0-9_.+*\/\-\s]+/
CMP.100: "CMP"
CMP_CONTENT: /(?:[^)()]+|\([^)]*\))+/
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
        flat = []
        for item in items:
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)
        return flat

    def param(self, items):
        return items[0]

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

    def OPCODE(self, token):  # noqa: N802
        return str(token)

    def TAG_BASE(self, token):  # noqa: N802
        return str(token)

    def NUMBER(self, token):  # noqa: N802
        return Operand(value=str(token))

    def WILDCARD(self, token):  # noqa: N802
        return Operand(value="?")

    def HEX_LITERAL(self, token):  # noqa: N802
        return Operand(value=str(token))

    def EXPR(self, token):  # noqa: N802
        return Operand(value=str(token).strip())

    def SEMICOLON(self, token):  # noqa: N802
        return None

    def CMP(self, token):  # noqa: N802
        return str(token)

    def CMP_CONTENT(self, token):  # noqa: N802
        return Operand(value=str(token).strip())


def _merge_branches(items: list) -> list[Instruction]:
    result: list[Instruction] = []
    for item in items:
        if isinstance(item, Instruction):
            result.append(item)
        elif isinstance(item, _BranchItem) and item.paths:
            if result:
                result[-1].branch = item.paths
    return result


_transformer = _RLLTransformer()
_parser = Lark(_GRAMMAR, parser="lalr", transformer=_transformer)


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
