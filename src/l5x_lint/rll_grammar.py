from lark import Lark, Transformer, UnexpectedInput
from dataclasses import dataclass, field


_GRAMMAR = r"""
start: rung+

rung: items SEMICOLON

items: item*

item: instruction
    | branch

instruction: OPCODE ("(" params? ")")?

branch: "[" items ("," items)* "]"

params: param ("," param)*

param: tag_path
     | NUMBER
     | WILDCARD
     | EXPR

tag_path: TAG_BASE ("." TAG_BASE)* ("[" NUMBER "]")*

// Tokens
OPCODE: /[A-Z][A-Z0-9_]*/

TAG_BASE: /[A-Za-z_][A-Za-z0-9_]*/
        | /[A-Za-z_]+:[0-9]+:[A-Za-z_]+/

WILDCARD: "?"

NUMBER: /-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?/

SEMICOLON: ";"

// Opaque expression for CPT etc. — captures everything up to closing paren/comma
// Must not contain ( ) ; to avoid stealing from other grammar rules
EXPR: /[A-Za-z0-9_.+*\/\-\s]+/

%ignore /[ \t\n\r]+/
"""


@dataclass
class Operand:
    type: str  # "tag", "number", "wildcard", "expression"
    value: str
    tag_parts: list[str] | None = None
    array_indices: list[int] | None = None


@dataclass
class Instruction:
    opcode: str
    operands: list[Operand] = field(default_factory=list)


@dataclass
class Branch:
    branches: list = field(default_factory=list)


@dataclass
class Rung:
    items: list = field(default_factory=list)


class RLLTransformer(Transformer):
    def start(self, items):
        return items

    def rung(self, items):
        flat = []
        for x in items:
            if isinstance(x, list):
                for y in x:
                    if isinstance(y, (Instruction, Branch)):
                        flat.append(y)
            elif isinstance(x, (Instruction, Branch)):
                flat.append(x)
        return Rung(items=flat)

    def items(self, items):
        return [x for x in items if x is not None]

    def item(self, items):
        return items[0] if items else None

    def instruction(self, items):
        opcode = str(items[0])
        operands = list(items[1]) if len(items) > 1 and items[1] else []
        return Instruction(opcode=opcode, operands=operands)

    def branch(self, items):
        return Branch(branches=[x for x in items if x is not None])

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
        parts = []
        indices = []
        for item in items:
            s = str(item)
            if s.startswith("["):
                indices.append(int(s.strip("[]")))
            elif isinstance(item, Operand):
                # NUMBER is transformed to Operand — extract raw value
                index_str = item.value
                indices.append(int(index_str))
            else:
                parts.append(s)
        return Operand(
            type="tag",
            value=".".join(parts) + "".join(f"[{i}]" for i in indices),
            tag_parts=parts,
            array_indices=indices or None,
        )

    def OPCODE(self, token):
        return str(token)

    def TAG_BASE(self, token):
        return str(token)

    def NUMBER(self, token):
        return Operand(type="number", value=str(token))

    def WILDCARD(self, token):
        return Operand(type="wildcard", value="?")

    def EXPR(self, token):
        return Operand(type="expression", value=str(token).strip())


parser = Lark(_GRAMMAR, parser="lalr", transformer=RLLTransformer())

RLL_TEST_CASES = [
    ("XIC(Start)OTE(Run);", True),
    ("XIO(Stop)OTE(Run);", True),
    ("XIC(A)XIC(B)OTE(C);", True),
    ("TON(Timer1,?,?);", True),
    ("TOF(Timer1,?,?);", True),
    ("CTU(Counter1,?,?);", True),
    ("XIC(A)[XIO(B),XIO(C)]OTE(D);", True),
    ("[XIC(A),XIC(B)]OTE(C);", True),
    ("MOV(42,Dest);", True),
    ("ADD(1,2,Result);", True),
    ("XIC(Timer1.DN)OTE(Output);", True),
    ("MOV(Timer1.ACC,Dest);", True),
    ("XIC(Array[5])OTE(Output);", True),
    ("XIC(CIP:0:MyTag)OTE(Output);", True),
    ("AFI;", True),
    ("NOP;", True),
    ("TND;", True),
    ("JSR(MyRoutine,Param1,Param2);", True),
    ("XIC(A)OTE(B)[OTL(C),OTU(D)];", True),
    ("XIC(Start)XIC(Enable)TON(Timer1,?,?)OTE(Complete);", True),
    ("OTE(Run);", True),
    ("XIC(A)[XIO(B),XIO(C)]OTE(D)[OTL(E)];", True),
    # Invalid
    ("XIC(A,B)OTE(D);", True),  # syntax ok, semantic issue
    ("INVALID123(Tag);", True),
    (";", False),  # Empty
]

parser_cache = Lark(_GRAMMAR, parser="lalr")


def parse(text: str) -> Rung:
    result = parser.parse(text)
    if isinstance(result, list):
        return result[0]
    return result


if __name__ == "__main__":
    passed = 0
    failed = 0
    results = []
    for text, should_pass in RLL_TEST_CASES:
        try:
            rung = parse(text)
            items_desc = []
            for item in rung.items:
                if isinstance(item, Instruction):
                    ops = ", ".join(o.value for o in item.operands)
                    items_desc.append(f"{item.opcode}({ops})")
                elif isinstance(item, Branch):
                    items_desc.append(f"[{len(item.branches)} paths]")
            desc = " | ".join(items_desc)
            status = "OK" if should_pass else "UNEXPECTED-PASS"
            if status == "OK":
                passed += 1
            else:
                failed += 1
                results.append(f"  [{status}] {text!r:50s} → {desc}")
            print(f"  [{status}] {text!r:50s} → {desc}")
        except UnexpectedInput as e:
            status = "PARSE-ERROR" if should_pass else "EXPECTED-FAIL"
            if status == "EXPECTED-FAIL":
                passed += 1
            else:
                failed += 1
                results.append(f"  [{status}] {text!r:50s} → {e}")
            print(f"  [{status}] {text!r:50s} → PARSE-ERROR")

    for r in results:
        print(r)
    print(f"\n{passed} passed, {failed} failed out of {len(RLL_TEST_CASES)}")
