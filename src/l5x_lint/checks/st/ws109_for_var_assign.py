from l5x_lint.checks._codes import WS109
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import StAssignment, StFor
from l5x_lint.pipeline.analyze import register


class ForVarAssignCheck(StWalker):
    def visit_for(self, node: StFor) -> None:
        if not node.variable.segments:
            return
        for_var = node.variable.segments[0].name.upper()
        for stmt in node.body:
            if isinstance(stmt, StAssignment) and stmt.target.segments:
                if stmt.target.segments[0].name.upper() == for_var:
                    self.add_diagnostic(
                        code=WS109.code,
                        severity=WS109.severity,
                        message=WS109(name=for_var.lower(), line=stmt.line).message,
                        line=stmt.line,
                    )


ws109_for_var_assign = ForVarAssignCheck()
register(ws109_for_var_assign)
