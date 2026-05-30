from l5x_lint.checks._codes import ER015
from l5x_lint.checks._walkers import RllWalker
from l5x_lint.pipeline.analyze import register


class Er015Check(RllWalker):
    def __call__(self, routine, symbols, loc):
        self.result = []
        self.symbols = symbols
        self.loc = loc
        if routine.type == "RLL" and routine.rll_rungs:
            mcr_count = 0
            for rung in routine.rll_rungs:
                self.rung_num = rung.number
                self.visit_rung(rung)
                mcr_count += _count_mcr(rung.instructions)
            if mcr_count % 2 != 0:
                self.add_diagnostic(
                    ER015.code, ER015.severity,
                    ER015(routine=routine.name).message,
                )
        return self.result


def _count_mcr(instructions) -> int:
    count = 0
    for inst in instructions:
        if inst.opcode.upper() == "MCR":
            count += 1
        if inst.branch:
            for path in inst.branch:
                count += _count_mcr(path)
    return count


er015_mcr_zone = Er015Check()
register(er015_mcr_zone)
