from application._registry import register
from domain.checks._codes import ER016
from domain.checks._walkers import RllWalker

_FILE_OPS: frozenset[str] = frozenset({"FAL", "FSC"})
_MIN_OPERANDS = 3


class Er016Check(RllWalker):
    def visit_instruction(self, inst) -> None:
        opcode = inst.opcode.upper()
        if opcode in _FILE_OPS and len(inst.operands) < _MIN_OPERANDS:
            self.add_diagnostic(
                ER016.code,
                ER016.severity,
                ER016(
                    opcode=opcode,
                    rung=self.rung_num,
                    actual=len(inst.operands),
                ).message,
                rung=self.rung_num,
            )


er016_fal_incomplete = Er016Check()
register(er016_fal_incomplete)
