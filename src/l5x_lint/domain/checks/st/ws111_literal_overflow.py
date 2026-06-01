from l5x_lint.domain.checks._codes import WS111
from l5x_lint.domain.checks._walkers import StWalker
from l5x_lint.domain.st_models import StLiteral
from l5x_lint.application.analyze import register

_DINT_MAX = 2_147_483_647
_DINT_MIN = -2_147_483_648


class Ws111Check(StWalker):
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

    def visit_call(self, node) -> None:
        self._current_line = node.line

    def visit_jsr(self, node) -> None:
        self._current_line = node.line

    def visit_binary_op(self, node) -> None:
        pass

    def visit_unary_op(self, node) -> None:
        pass

    def visit_literal(self, node: StLiteral) -> None:
        match node.value:
            case int(v):
                if v > _DINT_MAX or v < _DINT_MIN:
                    self.add_diagnostic(
                        WS111.code,
                        WS111.severity,
                        WS111(value=str(v), line=self._current_line).message,
                        line=self._current_line,
                    )
            case float(v):
                if v > 3.4e38 or v < -3.4e38:
                    self.add_diagnostic(
                        WS111.code,
                        WS111.severity,
                        WS111(value=str(v), line=self._current_line).message,
                        line=self._current_line,
                    )


ws111_literal_overflow = Ws111Check()
register(ws111_literal_overflow)
