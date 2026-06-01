from l5x_lint.checks._codes import WR005
from l5x_lint.checks._walkers import RllWalker
from l5x_lint.pipeline.analyze import register


class Wr005Check(RllWalker):
    def visit_instruction(self, inst) -> None:
        if inst.opcode.upper() == "NOP":
            self.add_diagnostic(
                WR005.code,
                WR005.severity,
                WR005(rung=self.rung_num).message,
                rung=self.rung_num,
            )


wr005_nop_present = Wr005Check()
register(wr005_nop_present)
