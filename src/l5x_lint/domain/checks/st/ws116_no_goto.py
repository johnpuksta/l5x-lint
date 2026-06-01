from l5x_lint.domain.checks._codes import WS116
from l5x_lint.domain.checks._walkers import StWalker
from l5x_lint.application.analyze import register


class Ws116NoGoto(StWalker):
    def visit_jsr(self, node) -> None:
        pass


ws116_no_goto = Ws116NoGoto()
register(ws116_no_goto)
