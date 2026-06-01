from l5x_lint.checks._codes import WS114
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import StBinaryOp, StLiteral, StTagRef
from l5x_lint.pipeline.analyze import register


def _type_label(expr) -> str | None:
    match expr:
        case StLiteral(value=int()):
            return "INT"
        case StLiteral(value=float()):
            return "REAL"
        case StLiteral(value=str()):
            return "STRING"
        case StLiteral(value=bool()):
            return "BOOL"
        case StTagRef():
            return "TAG"
    return None


class Ws114Check(StWalker):
    _current_line: int = 0

    def visit_assignment(self, node) -> None:
        self._current_line = node.line

    def visit_if(self, node) -> None:
        self._current_line = node.line

    def visit_case(self, node) -> None:
        self._current_line = node.line

    def visit_for(self, node) -> None:
        self._current_line = node.line

    def visit_while(self, node) -> None:
        self._current_line = node.line

    def visit_repeat(self, node) -> None:
        self._current_line = node.line

    def visit_binary_op(self, node: StBinaryOp) -> None:
        left_t = _type_label(node.left)
        right_t = _type_label(node.right)
        if left_t and right_t and left_t != right_t:
            if {left_t, right_t} == {"INT", "REAL"}:
                self.add_diagnostic(
                    WS114.code,
                    WS114.severity,
                    WS114(
                        line=self._current_line,
                        left_type=left_t,
                        right_type=right_t,
                    ).message,
                    line=self._current_line,
                )


ws114_implicit_cast = Ws114Check()
register(ws114_implicit_cast)
