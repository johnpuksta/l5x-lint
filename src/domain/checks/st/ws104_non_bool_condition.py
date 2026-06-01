from domain.checks._codes import WS104
from domain.checks._types import expression_type
from domain.checks._walkers import StWalker
from domain.st_models import StIf, StRepeat, StWhile
from application.analyze import register


class Ws104Check(StWalker):
    def visit_if(self, node: StIf) -> None:
        t = expression_type(node.condition, self.loc.program, self.symbols)
        if t is not None and t.upper() != "BOOL":
            self.add_diagnostic(
                WS104.code,
                WS104.severity,
                WS104(construct="IF", actual=t).message,
                line=node.line,
            )

    def visit_while(self, node: StWhile) -> None:
        t = expression_type(node.condition, self.loc.program, self.symbols)
        if t is not None and t.upper() != "BOOL":
            self.add_diagnostic(
                WS104.code,
                WS104.severity,
                WS104(construct="WHILE", actual=t).message,
                line=node.line,
            )

    def visit_repeat(self, node: StRepeat) -> None:
        if node.until is not None:
            t = expression_type(node.until, self.loc.program, self.symbols)
            if t is not None and t.upper() != "BOOL":
                self.add_diagnostic(
                    WS104.code,
                    WS104.severity,
                    WS104(construct="UNTIL", actual=t).message,
                    line=node.line,
                )


ws104_non_bool_condition = Ws104Check()
register(ws104_non_bool_condition)
