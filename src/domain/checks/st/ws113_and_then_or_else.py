from application.analyze import register
from domain.checks._codes import WS113
from domain.checks._types import expression_type
from domain.checks._walkers import StWalker
from domain.st_models import StBinaryOp

_SHORT_CIRCUIT_OPS: frozenset[str] = frozenset({"AND_THEN", "OR_ELSE"})


class Ws113Check(StWalker):
    def visit_binary_op(self, node: StBinaryOp) -> None:
        if node.op.upper() not in _SHORT_CIRCUIT_OPS:
            return
        for expr, side in ((node.left, "left"), (node.right, "right")):
            t = expression_type(expr, self.loc.program, self.symbols)
            if t is not None and t.upper() != "BOOL":
                self.add_diagnostic(
                    WS113.code,
                    WS113.severity,
                    WS113(op=node.op.upper(), actual=t).message,
                )


ws113_and_then_or_else = Ws113Check()
register(ws113_and_then_or_else)
