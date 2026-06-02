from application.analyze import register
from domain.checks._codes import ES002
from domain.checks._walkers import StWalker
from domain.st_models import StCase, StLiteral


def _value_str(expr) -> str | None:
    match expr:
        case StLiteral(value=v):
            return str(v)
        case _:
            return None


class ES002DuplicateCaseValueCheck(StWalker):
    def visit_case(self, node: StCase) -> None:
        seen: set[str] = set()
        for values, _ in node.cases:
            for v in values:
                val_str = _value_str(v)
                if val_str is not None:
                    if val_str in seen:
                        self.add_diagnostic(
                            code=ES002.code,
                            severity=ES002.severity,
                            message=ES002(value=val_str, line=node.line).message,
                            line=node.line,
                        )
                    else:
                        seen.add(val_str)


es002_duplicate_case_value = ES002DuplicateCaseValueCheck()
register(es002_duplicate_case_value)
