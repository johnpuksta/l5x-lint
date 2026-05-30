from l5x_lint.checks._codes import WC107
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import StCase, StIf
from l5x_lint.pipeline.analyze import register

_DEPRECATED_CALLS: frozenset[str] = frozenset({
    "MSG", "PID", "DDT", "FSC", "FAL",
})


class Wc107Check(StWalker):
    def visit_if(self, node: StIf) -> None:
        if node.condition and not node.body:
            self.add_diagnostic(
                WC107.code, WC107.severity,
                WC107(construct="IF").message,
                line=node.line,
            )
        for _cond, body in node.elsif_pairs:
            if not body:
                self.add_diagnostic(
                    WC107.code, WC107.severity,
                    WC107(construct="ELSIF").message,
                    line=node.line,
                )

    def visit_case(self, node: StCase) -> None:
        for _values, body in node.cases:
            if not body:
                self.add_diagnostic(
                    WC107.code, WC107.severity,
                    WC107(construct="CASE branch").message,
                    line=node.line,
                )


wc107_empty_body = Wc107Check()
register(wc107_empty_body)
