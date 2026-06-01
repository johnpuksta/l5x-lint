from l5x_lint.checks._codes import WS108
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import StCall
from l5x_lint.pipeline.analyze import register

_NO_EFFECT_CALLS: frozenset[str] = frozenset(
    {
        "ADD",
        "SUB",
        "MUL",
        "DIV",
        "MOD",
        "NEG",
        "ABS",
        "SQR",
        "GT",
        "LT",
        "GEQ",
        "LEQ",
        "EQU",
        "NEQ",
        "AND",
        "OR",
        "NOT",
        "XOR",
    }
)


class Ws108Check(StWalker):
    def visit_call(self, node: StCall) -> None:
        if node.name.upper() in _NO_EFFECT_CALLS:
            self.add_diagnostic(
                WS108.code,
                WS108.severity,
                WS108(line=node.line).message,
                line=node.line,
            )


ws108_no_effect = Ws108Check()
register(ws108_no_effect)
