from l5x_lint.checks._codes import WS105
from l5x_lint.checks._walkers import StWalker
from l5x_lint.domain.st_models import StAssignment, StTagRef
from l5x_lint.pipeline.analyze import register

_NARROW_TO_WIDE: dict[str, int] = {
    "SINT": 1,
    "INT": 2,
    "DINT": 4,
    "LINT": 8,
    "USINT": 1,
    "UINT": 2,
    "UDINT": 4,
    "ULINT": 8,
    "BOOL": 0,
    "REAL": 4,
    "LREAL": 8,
}


def _is_downcast(from_type: str, to_type: str) -> bool:
    fw = _NARROW_TO_WIDE.get(from_type.upper())
    tw = _NARROW_TO_WIDE.get(to_type.upper())
    if fw is None or tw is None:
        return False
    return fw > tw


class Ws105ImplicitDowncast(StWalker):
    def visit_assignment(self, node: StAssignment) -> None:
        if not node.target.segments:
            return
        target_name = node.target.segments[0].name
        target_type = self.symbols.resolve_type(target_name, self.loc.program)
        if target_type is None:
            return
        match node.expression:
            case StTagRef() if node.expression.path.segments:
                src_name = node.expression.path.segments[0].name
                src_type = self.symbols.resolve_type(src_name, self.loc.program)
                if src_type is not None and _is_downcast(
                    src_type.name, target_type.name
                ):
                    self.add_diagnostic(
                        code=WS105.code,
                        severity=WS105.severity,
                        message=WS105(
                            name=target_name,
                            from_type=src_type.name,
                            to_type=target_type.name,
                        ).message,
                        line=node.line,
                    )


ws105_implicit_downcast = Ws105ImplicitDowncast()
register(ws105_implicit_downcast)
