from l5x_lint.domain.checks._codes import ES001
from l5x_lint.domain.checks._types import expression_type
from l5x_lint.domain.checks._walkers import StWalker
from l5x_lint.domain.st_models import StBinaryOp
from l5x_lint.application.analyze import register

_STRING_TYPES: frozenset[str] = frozenset({"STRING"})


class ES001InvalidExpressionOpCheck(StWalker):
    def visit_binary_op(self, node: StBinaryOp) -> None:
        left_t = expression_type(node.left, self.loc.program, self.symbols)
        right_t = expression_type(node.right, self.loc.program, self.symbols)
        if left_t and right_t:
            lu = left_t.upper()
            ru = right_t.upper()
            msg = ES001(left_type=left_t, op=node.op, right_type=right_t).message
            if lu in _STRING_TYPES and ru not in _STRING_TYPES:
                self.add_diagnostic(ES001.code, ES001.severity, msg)
            elif ru in _STRING_TYPES and lu not in _STRING_TYPES:
                self.add_diagnostic(ES001.code, ES001.severity, msg)


es001_invalid_expression_op = ES001InvalidExpressionOpCheck()
register(es001_invalid_expression_op)
