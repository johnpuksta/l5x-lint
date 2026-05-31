from l5x_lint.checks._codes import WS118
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import StCase, StLiteral
from l5x_lint.pipeline.analyze import register


class Ws118CaseConstant(StWalker):
    def visit_case(self, node: StCase) -> None:
        for values, _ in node.cases:
            for v in values:
                if not isinstance(v, StLiteral):
                    self.add_diagnostic(
                        WS118.code, WS118.severity,
                        WS118(line=node.line).message,
                        line=node.line,
                    )
                    return


ws118_case_constant = Ws118CaseConstant()
register(ws118_case_constant)
