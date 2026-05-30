import re

from l5x_lint.checks._codes import WR008
from l5x_lint.checks._walkers import RllWalker
from l5x_lint.pipeline.analyze import register


_COPY_OPS: frozenset[str] = frozenset({"COP", "CPS"})

_tag_base_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")


def _base_tag(operand_value: str) -> str:
    m = _tag_base_re.match(operand_value)
    return m.group(1) if m else operand_value


class Wr008Check(RllWalker):
    def visit_instruction(self, inst) -> None:
        opcode = inst.opcode.upper()
        if opcode in _COPY_OPS and len(inst.operands) >= 2:
            src = _base_tag(inst.operands[0].value)
            dst = _base_tag(inst.operands[1].value)
            if src and dst and src == dst:
                self.add_diagnostic(
                    WR008.code, WR008.severity,
                    WR008(
                        source=inst.operands[0].value,
                        dest=inst.operands[1].value,
                        rung=self.rung_num,
                    ).message,
                    rung=self.rung_num,
                )


wr008_cop_overlap = Wr008Check()
register(wr008_cop_overlap)
