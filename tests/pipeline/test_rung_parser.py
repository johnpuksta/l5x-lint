from returns.result import Failure

from l5x_lint.pipeline.rung_parser import parse


def test_parse_single_instruction():
    result = parse("XIC(Start);")
    rungs = result.unwrap()
    assert len(rungs) == 1
    r = rungs[0]
    assert len(r.instructions) == 1
    assert r.instructions[0].opcode == "XIC"
    assert r.instructions[0].operands[0].value == "Start"


def test_parse_two_instructions():
    result = parse("XIC(Start)OTE(Run);")
    rungs = result.unwrap()
    assert len(rungs) == 1
    assert len(rungs[0].instructions) == 2
    assert rungs[0].instructions[0].opcode == "XIC"
    assert rungs[0].instructions[1].opcode == "OTE"


def test_parse_zero_operand_instruction():
    result = parse("AFI;")
    rungs = result.unwrap()
    assert len(rungs[0].instructions) == 1
    assert rungs[0].instructions[0].opcode == "AFI"
    assert rungs[0].instructions[0].operands == []


def test_parse_multiple_rungs():
    result = parse("XIC(A)OTE(B);XIC(C)OTE(D);")
    rungs = result.unwrap()
    assert len(rungs) == 2
    assert rungs[0].number == 0
    assert rungs[1].number == 1
    assert rungs[0].instructions[0].operands[0].value == "A"
    assert rungs[1].instructions[0].operands[0].value == "C"


def test_parse_with_branch():
    result = parse("XIC(A)[XIO(B),XIO(C)]OTE(D);")
    rungs = result.unwrap()
    assert len(rungs) == 1
    xic = rungs[0].instructions[0]
    assert xic.opcode == "XIC"
    assert xic.branch is not None
    assert len(xic.branch) == 2  # two parallel paths
    assert xic.branch[0][0].opcode == "XIO"
    assert xic.branch[0][0].operands[0].value == "B"
    assert xic.branch[1][0].opcode == "XIO"
    assert xic.branch[1][0].operands[0].value == "C"


def test_parse_instruction_with_multiple_operands():
    result = parse("TON(Timer1,?,?);")
    rungs = result.unwrap()
    assert len(rungs[0].instructions) == 1
    instr = rungs[0].instructions[0]
    assert instr.opcode == "TON"
    assert len(instr.operands) == 3
    assert instr.operands[0].value == "Timer1"
    assert instr.operands[1].value == "?"
    assert instr.operands[2].value == "?"


def test_parse_with_numbers():
    result = parse("MOV(42,Dest);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert instr.opcode == "MOV"
    assert instr.operands[0].value == "42"
    assert instr.operands[1].value == "Dest"


def test_parse_with_member_access():
    result = parse("XIC(Timer1.DN)OTE(Output);")
    rungs = result.unwrap()
    assert rungs[0].instructions[0].operands[0].value == "Timer1.DN"
    assert rungs[0].instructions[1].operands[0].value == "Output"


def test_parse_with_array_index():
    result = parse("XIC(Array[5])OTE(Output);")
    rungs = result.unwrap()
    assert rungs[0].instructions[0].operands[0].value == "Array[5]"


def test_parse_with_communication_tag():
    result = parse("XIC(CIP:0:MyTag)OTE(Output);")
    rungs = result.unwrap()
    assert rungs[0].instructions[0].operands[0].value == "CIP:0:MyTag"


def test_parse_jsr_with_params():
    result = parse("JSR(MyRoutine,Param1,Param2);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert instr.opcode == "JSR"
    assert len(instr.operands) == 3
    assert instr.operands[1].value == "Param1"


def test_parse_output_branch():
    result = parse("XIC(A)[XIO(B),XIO(C)]OTE(D)[OTL(E)];")
    rungs = result.unwrap()
    assert len(rungs[0].instructions) == 2
    assert rungs[0].instructions[0].opcode == "XIC"
    assert rungs[0].instructions[0].branch is not None
    assert rungs[0].instructions[1].opcode == "OTE"
    # second branch attaches to OTE
    assert rungs[0].instructions[1].branch is not None
    assert len(rungs[0].instructions[1].branch) == 1


def test_parse_empty_text():
    result = parse("")
    rungs = result.unwrap()
    assert rungs == []


def test_parse_whitespace_only():
    result = parse("   \n  \t  ")
    rungs = result.unwrap()
    assert rungs == []


def test_parse_without_semicolon():
    result = parse("XIC(A)OTE(B)")
    rungs = result.unwrap()
    assert len(rungs) == 1
    assert len(rungs[0].instructions) == 2


def test_parse_missing_closing_paren():
    result = parse("XIC(A")
    assert isinstance(result, Failure)


def test_parse_invalid_token():
    result = parse("@invalid!;")
    assert isinstance(result, Failure)


def test_parse_member_with_array():
    result = parse("MOV(Array[2].Member,Dest);")
    rungs = result.unwrap()
    assert rungs[0].instructions[0].operands[0].value == "Array[2].Member"


def test_parse_expression_operand():
    result = parse("CPT(Dest, A+B*C);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert instr.opcode == "CPT"
    # second operand is expression
    assert instr.operands[1].value == "A+B*C"


def test_parse_rung_numbering():
    result = parse("XIC(A);XIO(B);OTE(C);")
    rungs = result.unwrap()
    assert len(rungs) == 3
    for i, r in enumerate(rungs):
        assert r.number == i


def test_parse_leading_whitespace():
    result = parse("  \n  XIC(A)OTE(B);")
    rungs = result.unwrap()
    assert len(rungs) == 1


def test_parse_empty_branch():
    result = parse("XIC(A)[]OTE(B);")
    rungs = result.unwrap()
    # empty branch just attaches as empty list
    assert len(rungs[0].instructions) == 2


def test_parse_branch_on_output():
    result = parse("XIC(A)OTE(B)[OTL(C)];")
    rungs = result.unwrap()
    ote = rungs[0].instructions[1]
    assert ote.branch is not None
    assert ote.branch[0][0].opcode == "OTL"
    assert ote.branch[0][0].operands[0].value == "C"


def test_parse_complex_rung():
    text = "XIC(A)XIC(Enable)TON(Timer1,?,?)OTE(Complete);"
    result = parse(text)
    rungs = result.unwrap()
    assert len(rungs[0].instructions) == 4
    assert rungs[0].instructions[0].opcode == "XIC"
    assert rungs[0].instructions[2].operands[0].value == "Timer1"


def test_parse_single_instruction_no_parens():
    result = parse("AFI;")
    rungs = result.unwrap()
    assert rungs[0].instructions[0].opcode == "AFI"
    assert rungs[0].instructions[0].operands == []


def test_parse_multiple_branches():
    result = parse("XIC(A)[XIO(B)XIC(C),XIO(D)]OTE(E);")
    rungs = result.unwrap()
    branch = rungs[0].instructions[0].branch
    assert branch is not None
    assert len(branch) == 2
    assert len(branch[0]) == 2  # XIO(B) and XIC(C) are in same path
    assert branch[0][0].opcode == "XIO"
    assert branch[0][1].opcode == "XIC"
    assert branch[1][0].opcode == "XIO"


def test_parse_realistic_rung():
    text = "XIC(Motor_Start)XIC(Safety_Ok)[XIO(E_Stop),XIC(Auto_Mode)]OTE(Motor_Run);"
    result = parse(text)
    rungs = result.unwrap()
    assert len(rungs) == 1
    assert rungs[0].instructions[0].operands[0].value == "Motor_Start"
    assert rungs[0].instructions[1].operands[0].value == "Safety_Ok"
    assert rungs[0].instructions[1].branch is not None
    assert len(rungs[0].instructions[1].branch) == 2
