from l5x_lint.checks._codes import WS115
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import StRepeat
from l5x_lint.pipeline.analyze import register


class Ws115NoRepeat(StWalker):
    def visit_repeat(self, node: StRepeat) -> None:
        self.add_diagnostic(
            WS115.code, WS115.severity,
            WS115(line=node.line).message,
            line=node.line,
        )


ws115_no_repeat = Ws115NoRepeat()
register(ws115_no_repeat)
