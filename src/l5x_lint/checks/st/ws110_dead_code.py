from l5x_lint.checks._codes import WS110
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import (
    StCase, StExit, StFor, StIf, StProgram, StRepeat, StReturn, StWhile,
)
from l5x_lint.pipeline.analyze import register


class Ws110DeadCode(StWalker):
    def __call__(self, routine, symbols, loc):
        self.result = []
        self.symbols = symbols
        self.loc = loc
        bod = routine.st_body
        if isinstance(bod, StProgram):
            self._check_body(bod.statements)
        return self.result

    def _check_body(self, stmts):
        for i, stmt in enumerate(stmts):
            match stmt:
                case StReturn():
                    self._remaining = stmts[i + 1:]
                    self.visit_return(stmt)
                    return
                case StExit():
                    self._remaining = stmts[i + 1:]
                    self.visit_exit(stmt)
                    return
                case StIf():
                    self.visit_if(stmt)
                    self._check_body(stmt.body)
                    for _, body in stmt.elsif_pairs:
                        self._check_body(body)
                    self._check_body(stmt.else_body)
                case StCase():
                    self.visit_case(stmt)
                    for _, body in stmt.cases:
                        self._check_body(body)
                    self._check_body(stmt.else_body)
                case StFor():
                    self.visit_for(stmt)
                    self._check_body(stmt.body)
                case StWhile():
                    self.visit_while(stmt)
                    self._check_body(stmt.body)
                case StRepeat():
                    self.visit_repeat(stmt)
                    self._check_body(stmt.body)

    def visit_return(self, node: StReturn) -> None:
        for dead in self._remaining:
            self.add_diagnostic(
                WS110.code, WS110.severity,
                WS110(construct="RETURN", line=node.line).message,
                line=getattr(dead, 'line', 0),
            )

    def visit_exit(self, node: StExit) -> None:
        for dead in self._remaining:
            self.add_diagnostic(
                WS110.code, WS110.severity,
                WS110(construct="EXIT", line=node.line).message,
                line=getattr(dead, 'line', 0),
            )


ws110_dead_code = Ws110DeadCode()
register(ws110_dead_code)
