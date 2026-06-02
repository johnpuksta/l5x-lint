from application._registry import register
from domain.checks._codes import WC108
from domain.checks._walkers import RllWalker, StWalker
from domain.st_models import StCall

_DEPRECATED_INSTRUCTIONS: frozenset[str] = frozenset(
    {
        "MSG",
        "PID",
        "DDT",
    }
)


class _StWc108Check(StWalker):
    def visit_call(self, node: StCall) -> None:
        if node.name.upper() in _DEPRECATED_INSTRUCTIONS:
            self.add_diagnostic(
                WC108.code,
                WC108.severity,
                WC108(opcode=node.name, line=node.line).message,
                line=node.line,
            )


class _RllWc108Check(RllWalker):
    def visit_instruction(self, inst) -> None:
        if inst.opcode.upper() in _DEPRECATED_INSTRUCTIONS:
            self.add_diagnostic(
                WC108.code,
                WC108.severity,
                WC108(opcode=inst.opcode, line=0).message,
                rung=self.rung_num,
            )


wc108_st_deprecated = _StWc108Check()
wc108_rll_deprecated = _RllWc108Check()
register(wc108_st_deprecated)
register(wc108_rll_deprecated)
