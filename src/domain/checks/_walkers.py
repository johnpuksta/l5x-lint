"""AST walkers for ST and RLL check rules.

Usage:
    from domain.checks._walkers import StWalker, RllWalker
    from application.analyze import register

    class MyCheck(StWalker):
        def visit_if(self, node):
            self.add_diagnostic("WSXXX", "warning", "missing else", line=node.line)

    my_check = MyCheck()
    register(my_check)

- **StWalker** — walks ST programs; override visit_* methods
- **RllWalker** — walks RLL rungs/instructions (includes branch recursion)
- Both match `CheckFn` signature for `register(check_instance)`
- Default visit methods are no-ops; only override what you need
"""

from __future__ import annotations

from domain.diagnostics import Diagnostic
from domain.models import Location, Routine
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
from domain.symbols import SymbolTable


class StWalker:
    result: list[Diagnostic]
    symbols: SymbolTable
    loc: Location

    def __call__(
        self,
        routine: Routine,
        symbols: SymbolTable,
        loc: Location,
    ) -> list[Diagnostic]:
        self.result = []
        self.symbols = symbols
        self.loc = loc
        bod = routine.st_body
        if isinstance(bod, StProgram):
            for stmt in bod.statements:
                self._walk_stmt(stmt)
        return self.result

    def add_diagnostic(
        self,
        code: str,
        severity: str,
        message: str,
        line: int | None = None,
    ) -> None:
        self.result.append(
            Diagnostic(
                code=code,
                severity=severity,
                location=Location(
                    program=self.loc.program,
                    routine=self.loc.routine,
                    line=line,
                ),
                message=message,
            )
        )

    def _walk_stmt(self, stmt) -> None:
        match stmt:
            case StAssignment():
                self.visit_assignment(stmt)
                self._walk_expr(stmt.expression)
            case StIf():
                self.visit_if(stmt)
                self._walk_expr(stmt.condition)
                for s in stmt.body:
                    self._walk_stmt(s)
                for cond, body in stmt.elsif_pairs:
                    self._walk_expr(cond)
                    for s in body:
                        self._walk_stmt(s)
                for s in stmt.else_body:
                    self._walk_stmt(s)
            case StCase():
                self.visit_case(stmt)
                self._walk_expr(stmt.expression)
                for _, body in stmt.cases:
                    for s in body:
                        self._walk_stmt(s)
                for s in stmt.else_body:
                    self._walk_stmt(s)
            case StFor():
                self.visit_for(stmt)
                self._walk_expr(stmt.start)
                self._walk_expr(stmt.end)
                if stmt.step is not None:
                    self._walk_expr(stmt.step)
                for s in stmt.body:
                    self._walk_stmt(s)
            case StWhile():
                self.visit_while(stmt)
                self._walk_expr(stmt.condition)
                for s in stmt.body:
                    self._walk_stmt(s)
            case StRepeat():
                self.visit_repeat(stmt)
                for s in stmt.body:
                    self._walk_stmt(s)
                if stmt.until is not None:
                    self._walk_expr(stmt.until)
            case StCall():
                self.visit_call(stmt)
                for a in stmt.args:
                    self._walk_expr(a)
            case StJsr():
                self.visit_jsr(stmt)
                for a in stmt.args:
                    self._walk_expr(a)
            case StExit():
                self.visit_exit(stmt)
            case StReturn():
                self.visit_return(stmt)
            case StBinaryOp():
                self.visit_binary_op(stmt)
                self._walk_expr(stmt.left)
                self._walk_expr(stmt.right)
            case StUnaryOp():
                self.visit_unary_op(stmt)
                self._walk_expr(stmt.operand)

    def _walk_expr(self, expr) -> None:
        match expr:
            case StBinaryOp():
                self.visit_binary_op(expr)
                self._walk_expr(expr.left)
                self._walk_expr(expr.right)
            case StUnaryOp():
                self.visit_unary_op(expr)
                self._walk_expr(expr.operand)
            case StTagRef():
                self.visit_tag_ref(expr)
            case StLiteral():
                self.visit_literal(expr)
            case StCall():
                self.visit_call(expr)
                for a in expr.args:
                    self._walk_expr(a)

    def visit_assignment(self, node: StAssignment) -> None:
        pass

    def visit_if(self, node: StIf) -> None:
        pass

    def visit_case(self, node: StCase) -> None:
        pass

    def visit_for(self, node: StFor) -> None:
        pass

    def visit_while(self, node: StWhile) -> None:
        pass

    def visit_repeat(self, node: StRepeat) -> None:
        pass

    def visit_call(self, node: StCall) -> None:
        pass

    def visit_jsr(self, node: StJsr) -> None:
        pass

    def visit_exit(self, node: StExit) -> None:
        pass

    def visit_return(self, node: StReturn) -> None:
        pass

    def visit_binary_op(self, node: StBinaryOp) -> None:
        pass

    def visit_unary_op(self, node: StUnaryOp) -> None:
        pass

    def visit_tag_ref(self, node: StTagRef) -> None:
        pass

    def visit_literal(self, node: StLiteral) -> None:
        pass


class RllWalker:
    result: list[Diagnostic]
    symbols: SymbolTable
    loc: Location
    rung_num: int

    def __call__(
        self,
        routine: Routine,
        symbols: SymbolTable,
        loc: Location,
    ) -> list[Diagnostic]:
        self.result = []
        self.symbols = symbols
        self.loc = loc
        if routine.type == "RLL" and routine.rll_rungs:
            for rung in routine.rll_rungs:
                self.rung_num = rung.number
                self.visit_rung(rung)
                self._walk_instructions(rung.instructions)
        return self.result

    def add_diagnostic(
        self,
        code: str,
        severity: str,
        message: str,
        rung: int | None = None,
    ) -> None:
        self.result.append(
            Diagnostic(
                code=code,
                severity=severity,
                location=Location(
                    program=self.loc.program,
                    routine=self.loc.routine,
                    rung=rung,
                ),
                message=message,
            )
        )

    def _walk_instructions(self, instructions) -> None:
        for inst in instructions:
            self.visit_instruction(inst)
            if inst.branch:
                for path in inst.branch:
                    self._walk_instructions(path)

    def visit_rung(self, node) -> None:
        pass

    def visit_instruction(self, node) -> None:
        pass
