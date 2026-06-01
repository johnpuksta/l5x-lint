from l5x_lint.checks._codes import ES003
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import StFor, StLiteral
from l5x_lint.pipeline.analyze import register

_DINT_MAX = 2_147_483_647
_DINT_MIN = -2_147_483_648


def _check_bound(value: object, label: str) -> str | None:
    match value:
        case StLiteral(value=int(v)):
            if v > _DINT_MAX:
                return f"{label} = {v} exceeds DINT maximum ({_DINT_MAX})"
            if v < _DINT_MIN:
                return f"{label} = {v} below DINT minimum ({_DINT_MIN})"
        case StLiteral(value=float(v)):
            if v > 3.4e38:
                return f"{label} = {v} exceeds REAL maximum"
            if v < -3.4e38:
                return f"{label} = {v} below REAL minimum"
    return None


class Es003Check(StWalker):
    def visit_for(self, node: StFor) -> None:
        for bound, label in [(node.start, "start"), (node.end, "end")]:
            detail = _check_bound(bound, label)
            if detail is not None:
                self.add_diagnostic(
                    ES003.code,
                    ES003.severity,
                    ES003(line=node.line, detail=detail).message,
                    line=node.line,
                )
        if node.step is not None:
            detail = _check_bound(node.step, "step")
            if detail is not None:
                self.add_diagnostic(
                    ES003.code,
                    ES003.severity,
                    ES003(line=node.line, detail=detail).message,
                    line=node.line,
                )


es003_for_bounds = Es003Check()
register(es003_for_bounds)
