from __future__ import annotations

from domain.checks._walkers import RllWalker, StWalker
from domain.models import (
    Controller,
    Location,
    Routine,
    TagPath,
    TagPathSegment,
)
from domain.rll_models import Instruction, Operand, ParsedRung
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
from domain.symbols import build_symbol_table


def _loc(program="", routine=""):
    return Location(program=program, routine=routine)


# ---------------------------------------------------------------------------
# StWalker – visit ordering
# ---------------------------------------------------------------------------


class _VisitRecorder(StWalker):
    def __init__(self):
        self.visited: list[str] = []

    def visit_assignment(self, node):
        self.visited.append("assignment")

    def visit_if(self, node):
        self.visited.append("if")

    def visit_case(self, node):
        self.visited.append("case")

    def visit_for(self, node):
        self.visited.append("for")

    def visit_while(self, node):
        self.visited.append("while")

    def visit_repeat(self, node):
        self.visited.append("repeat")

    def visit_call(self, node):
        self.visited.append("call")

    def visit_jsr(self, node):
        self.visited.append("jsr")

    def visit_exit(self, node):
        self.visited.append("exit")

    def visit_return(self, node):
        self.visited.append("return")

    def visit_binary_op(self, node):
        self.visited.append("binary_op")

    def visit_unary_op(self, node):
        self.visited.append("unary_op")

    def visit_tag_ref(self, node):
        self.visited.append("tag_ref")

    def visit_literal(self, node):
        self.visited.append("literal")


TP = lambda name: TagPath(segments=[TagPathSegment(name=name)])  # noqa: E731


def test_st_walks_assignment():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StAssignment(target=TP("x"), expression=StLiteral(value=1)),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["assignment", "literal"]


def test_st_walks_if():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StIf(
                condition=StLiteral(value=True),
                body=[StReturn()],
                elsif_pairs=[(StLiteral(value=False), [StExit()])],
                else_body=[StAssignment(target=TP("x"), expression=StLiteral(value=0))],
            ),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == [
        "if",
        "literal",
        "return",
        "literal",
        "exit",
        "assignment",
        "literal",
    ]


def test_st_walks_case():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StCase(
                expression=StTagRef(TP("x")),
                cases=[([StLiteral(1)], [StReturn()])],
                else_body=[StExit()],
            ),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["case", "tag_ref", "return", "exit"]


def test_st_walks_for():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StFor(
                variable=TP("i"),
                start=StLiteral(0),
                end=StLiteral(10),
                step=StLiteral(1),
                body=[StReturn()],
            ),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["for", "literal", "literal", "literal", "return"]


def test_st_walks_while():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StWhile(
                condition=StTagRef(TP("ok")),
                body=[StAssignment(target=TP("x"), expression=StLiteral(1))],
            ),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["while", "tag_ref", "assignment", "literal"]


def test_st_walks_repeat():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StRepeat(body=[StReturn()], until=StLiteral(True)),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["repeat", "return", "literal"]


def test_st_walks_call():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StCall(name="ADD", args=[StLiteral(1), StLiteral(2)]),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["call", "literal", "literal"]


def test_st_walks_jsr():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StJsr(routine_name="Sub", args=[StLiteral(99)]),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["jsr", "literal"]


def test_st_walks_exit():
    w = _VisitRecorder()
    prog = StProgram(statements=[StExit()])
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["exit"]


def test_st_walks_return():
    w = _VisitRecorder()
    prog = StProgram(statements=[StReturn()])
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["return"]


def test_st_walks_expr_binary_op():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StAssignment(
                target=TP("x"),
                expression=StBinaryOp(left=StLiteral(1), op="+", right=StLiteral(2)),
            ),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["assignment", "binary_op", "literal", "literal"]


def test_st_walks_expr_unary_op():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StAssignment(
                target=TP("x"),
                expression=StUnaryOp(op="-", operand=StLiteral(5)),
            ),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["assignment", "unary_op", "literal"]


def test_st_walks_expr_call():
    w = _VisitRecorder()
    prog = StProgram(
        statements=[
            StAssignment(
                target=TP("x"),
                expression=StCall(name="ABS", args=[StLiteral(-1)]),
            ),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    w(r, build_symbol_table(c), _loc())
    assert w.visited == ["assignment", "call", "literal"]


def test_st_non_st_ignored():
    w = _VisitRecorder()
    r = Routine(name="R", type="RLL")
    c = Controller(name="C")
    result = w(r, build_symbol_table(c), _loc())
    assert result == []


# ---------------------------------------------------------------------------
# StWalker – add_diagnostic helper
# ---------------------------------------------------------------------------


class _StDiagCollector(StWalker):
    def visit_if(self, node):
        self.add_diagnostic("WS107", "warning", "missing else", line=node.line)


def test_st_walker_add_diagnostic():
    w = _StDiagCollector()
    prog = StProgram(
        statements=[
            StIf(condition=StLiteral(True), body=[], line=5),
        ]
    )
    r = Routine(name="R", type="ST", st_body=prog)
    c = Controller(name="C")
    result = w(r, build_symbol_table(c), _loc(program="P", routine="R"))
    assert len(result) == 1
    assert result[0].code == "WS107"
    assert result[0].severity == "warning"
    assert result[0].location.program == "P"
    assert result[0].location.routine == "R"
    assert result[0].location.line == 5
    assert result[0].message == "missing else"


# ---------------------------------------------------------------------------
# RllWalker – visit ordering
# ---------------------------------------------------------------------------


class _RllVisitRecorder(RllWalker):
    def __init__(self):
        self.visited: list[str] = []

    def visit_rung(self, node):
        self.visited.append(f"rung({node.number})")

    def visit_instruction(self, node):
        self.visited.append(f"inst({node.opcode})")


def test_rll_walks_basic():
    w = _RllVisitRecorder()
    prog = Routine(
        name="R",
        type="RLL",
        rll_rungs=[
            ParsedRung(
                number=1,
                text="",
                instructions=[
                    Instruction(opcode="XIC", operands=[Operand("In1")]),
                    Instruction(opcode="OTE", operands=[Operand("Out1")]),
                ],
            ),
            ParsedRung(
                number=2,
                text="",
                instructions=[
                    Instruction(opcode="TON", operands=[Operand("T1")]),
                ],
            ),
        ],
    )
    c = Controller(name="C")
    w(prog, build_symbol_table(c), _loc())
    assert w.visited == [
        "rung(1)",
        "inst(XIC)",
        "inst(OTE)",
        "rung(2)",
        "inst(TON)",
    ]


def test_rll_walks_branches():
    w = _RllVisitRecorder()
    prog = Routine(
        name="R",
        type="RLL",
        rll_rungs=[
            ParsedRung(
                number=1,
                text="",
                instructions=[
                    Instruction(
                        opcode="XIC",
                        operands=[Operand("A")],
                        branch=[
                            [Instruction(opcode="OTE", operands=[Operand("B")])],
                            [Instruction(opcode="OTL", operands=[Operand("C")])],
                        ],
                    ),
                ],
            ),
        ],
    )
    c = Controller(name="C")
    w(prog, build_symbol_table(c), _loc())
    assert w.visited == [
        "rung(1)",
        "inst(XIC)",
        "inst(OTE)",
        "inst(OTL)",
    ]


def test_rll_non_rll_ignored():
    w = _RllVisitRecorder()
    r = Routine(name="R", type="ST")
    c = Controller(name="C")
    result = w(r, build_symbol_table(c), _loc())
    assert result == []


# ---------------------------------------------------------------------------
# RllWalker – add_diagnostic helper
# ---------------------------------------------------------------------------


class _RllDiagCollector(RllWalker):
    def visit_instruction(self, node):
        if node.opcode == "NOP":
            self.add_diagnostic("WR005", "warning", "NOP present", rung=self.rung_num)


def test_rll_walker_add_diagnostic():
    w = _RllDiagCollector()
    prog = Routine(
        name="R",
        type="RLL",
        rll_rungs=[
            ParsedRung(
                number=3,
                text="",
                instructions=[
                    Instruction(opcode="NOP", operands=[]),
                ],
            ),
        ],
    )
    c = Controller(name="C")
    result = w(prog, build_symbol_table(c), _loc(program="P", routine="R"))
    assert len(result) == 1
    assert result[0].code == "WR005"
    assert result[0].severity == "warning"
    assert result[0].location.rung == 3
    assert result[0].location.program == "P"
    assert result[0].message == "NOP present"


def test_rll_walker_add_diagnostic_default_rung():
    w = _RllDiagCollector()
    prog = Routine(
        name="R",
        type="RLL",
        rll_rungs=[
            ParsedRung(
                number=7,
                text="",
                instructions=[
                    Instruction(opcode="NOP", operands=[]),
                ],
            ),
        ],
    )
    c = Controller(name="C")
    result = w(prog, build_symbol_table(c), _loc())
    assert result[0].location.rung == 7
