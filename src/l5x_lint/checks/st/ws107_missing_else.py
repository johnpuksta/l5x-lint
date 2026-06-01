from l5x_lint.checks._codes import WS107
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import StCase, StIf
from l5x_lint.pipeline.analyze import register


class Ws107Check(StWalker):
    def visit_if(self, node: StIf) -> None:
        if not node.else_body:
            self.add_diagnostic(
                WS107.code,
                WS107.severity,
                WS107(construct="IF").message,
            )

    def visit_case(self, node: StCase) -> None:
        if not node.else_body:
            self.add_diagnostic(
                WS107.code,
                WS107.severity,
                WS107(construct="CASE").message,
            )


ws107_missing_else = Ws107Check()
register(ws107_missing_else)
