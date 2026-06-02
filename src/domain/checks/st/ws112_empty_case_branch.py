from application.analyze import register
from domain.checks._codes import WS112
from domain.checks._walkers import StWalker


class Ws112Check(StWalker):
    def visit_case(self, node) -> None:
        for selectors, body in node.cases:
            if not body:
                self.add_diagnostic(
                    WS112.code,
                    WS112.severity,
                    WS112(line=node.line).message,
                    line=node.line,
                )


ws112_empty_case_branch = Ws112Check()
register(ws112_empty_case_branch)
