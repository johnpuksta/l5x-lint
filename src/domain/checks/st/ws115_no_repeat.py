from domain.checks._codes import WS115
from domain.checks._walkers import StWalker
from domain.st_models import StRepeat
from application.analyze import register


class Ws115NoRepeat(StWalker):
    def visit_repeat(self, node: StRepeat) -> None:
        self.add_diagnostic(
            WS115.code,
            WS115.severity,
            WS115(line=node.line).message,
            line=node.line,
        )


ws115_no_repeat = Ws115NoRepeat()
register(ws115_no_repeat)
