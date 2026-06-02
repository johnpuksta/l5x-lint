from application.analyze import register
from domain.checks._codes import WR009
from domain.checks._walkers import RllWalker

_KNOWN_OBJECT_CLASSES: frozenset[str] = frozenset(
    {
        "Program",
        "Controller",
        "Task",
        "Module",
        "SerialPort",
        "DF1Port",
        "Message",
        "FaultLog",
        "Axis",
        "CoordinateSystem",
        "InputData",
        "OutputData",
        "CSNX_Backplane",
        "SafetyPartner",
        "WallClockTime",
        "CST",
        "DateTime",
        "LocalDateTime",
        "MotionGroup",
        "Drive",
        "Axis_Grouped",
        "AnalogInput",
        "AnalogOutput",
        "DigitalInput",
        "DigitalOutput",
    }
)


class Wr009Check(RllWalker):
    def visit_instruction(self, inst) -> None:
        opcode = inst.opcode.upper()
        if opcode in ("GSV", "SSV") and inst.operands:
            obj_class = inst.operands[0].value
            if obj_class not in _KNOWN_OBJECT_CLASSES:
                self.add_diagnostic(
                    WR009.code,
                    WR009.severity,
                    WR009(
                        obj_class=obj_class,
                        rung=self.rung_num,
                    ).message,
                    rung=self.rung_num,
                )


wr009_gsv_invalid_class = Wr009Check()
register(wr009_gsv_invalid_class)
