from application.analyze import register
from domain.checks._walkers import StWalker


class Ws116NoGoto(StWalker):
    def visit_jsr(self, node) -> None:
        pass


ws116_no_goto = Ws116NoGoto()
register(ws116_no_goto)
