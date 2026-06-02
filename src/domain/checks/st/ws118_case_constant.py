from application._registry import register
from domain.checks._codes import WS118
from domain.checks._walkers import StWalker
from domain.st_models import StCase, StLiteral


class Ws118CaseConstant(StWalker):
    def visit_case(self, node: StCase) -> None:
        for values, _ in node.cases:
            for v in values:
                if not isinstance(v, StLiteral):
                    self.add_diagnostic(
                        WS118.code,
                        WS118.severity,
                        WS118(line=node.line).message,
                        line=node.line,
                    )
                    return


ws118_case_constant = Ws118CaseConstant()
register(ws118_case_constant)
