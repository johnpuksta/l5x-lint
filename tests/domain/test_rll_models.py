from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung


def test_operand_simple():
    op = Operand("Motor_Run")
    assert op.value == "Motor_Run"
    assert op.type_hint is None


def test_operand_with_hint():
    op = Operand("Motor_Run", "BOOL")
    assert op.type_hint == "BOOL"


def test_instruction_no_operands():
    instr = Instruction("AFI")
    assert instr.opcode == "AFI"
    assert instr.operands == []


def test_instruction_with_operands():
    op = Operand("Start")
    instr = Instruction("XIC", [op])
    assert len(instr.operands) == 1


def test_instruction_with_branch():
    branch = [[Instruction("XIO", [Operand("B")]), Instruction("XIO", [Operand("C")])]]
    instr = Instruction("XIC", [Operand("A")], branch=branch)
    assert instr.branch is not None
    assert len(instr.branch[0]) == 2


def test_instruction_output_branch():
    instr = Instruction("OTE", [Operand("D")], is_output_branch=True)
    assert instr.is_output_branch


def test_parsed_rung_minimal():
    rung = ParsedRung(0, "XIC(Start)OTE(Run);")
    assert rung.number == 0
    assert rung.text == "XIC(Start)OTE(Run);"
    assert rung.instructions == []


def test_parsed_rung_with_instructions():
    instrs = [
        Instruction("XIC", [Operand("Start")]),
        Instruction("OTE", [Operand("Run")]),
    ]
    rung = ParsedRung(0, "XIC(Start)OTE(Run);", instructions=instrs)
    assert len(rung.instructions) == 2
    assert rung.instructions[0].opcode == "XIC"
