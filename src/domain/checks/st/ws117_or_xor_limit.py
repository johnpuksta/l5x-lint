from application.analyze import register
from domain.checks._codes import WS117
from domain.checks._walkers import StWalker
from domain.st_models import StBinaryOp

_OR_XOR: frozenset[str] = frozenset({"OR", "XOR"})


class Ws117OrXorLimit(StWalker):
    def visit_binary_op(self, node: StBinaryOp) -> None:
        if node.op.upper() in _OR_XOR:
            self.add_diagnostic(
                WS117.code,
                WS117.severity,
                WS117().message,
            )


ws117_or_xor_limit = Ws117OrXorLimit()
register(ws117_or_xor_limit)
