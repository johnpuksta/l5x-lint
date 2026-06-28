from application._registry import register
from domain.checks._codes import WS108
from domain.checks._opcode_sets import ST_PURE_CALLS
from domain.checks._walkers import StWalker
from domain.st_models import StCall


class Ws108Check(StWalker):
    def visit_call(self, node: StCall) -> None:
        if node.name.upper() in ST_PURE_CALLS:
            self.add_diagnostic(
                WS108.code,
                WS108.severity,
                WS108(line=node.line).message,
                line=node.line,
            )


ws108_no_effect = Ws108Check()
register(ws108_no_effect)
