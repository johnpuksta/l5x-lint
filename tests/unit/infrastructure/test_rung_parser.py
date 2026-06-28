from returns.result import Failure

from infrastructure.rung_parser import parse


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
    assert rungs[0].instructions[0].operands[0].value == "Array.5"


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
    assert rungs[0].instructions[0].operands[0].value == "Array.2.Member"


def test_parse_expression_operand():
    result = parse("CPT(Dest, A+B*C);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert instr.opcode == "CPT"
    # second operand is expression
    assert instr.operands[1].value == "A + B * C"


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


def test_io_address_suffix_si():
    result = parse("XIC(SignalA:SI)OTE(Flag);")
    rungs = result.unwrap()
    assert len(rungs) == 1
    assert rungs[0].instructions[0].operands[0].value == "SignalA:SI"
    assert rungs[0].instructions[1].operands[0].value == "Flag"


def test_io_address_suffix_so():
    result = parse("OTE(SignalB:SO);")
    rungs = result.unwrap()
    assert rungs[0].instructions[0].operands[0].value == "SignalB:SO"


def test_empty_operands_middle():
    result = parse("CAL(TagA,,TagB,TagC);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert instr.opcode == "CAL"
    assert len(instr.operands) == 4
    assert instr.operands[0].value == "TagA"
    assert instr.operands[1].value == ""
    assert instr.operands[2].value == "TagB"
    assert instr.operands[3].value == "TagC"


def test_empty_operands_trailing():
    result = parse("CAL(X,Y,,);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert len(instr.operands) == 4
    assert instr.operands[0].value == "X"
    assert instr.operands[1].value == "Y"
    assert instr.operands[2].value == ""
    assert instr.operands[3].value == ""


def test_hex_literal_with_underscores():
    result = parse("MOV(16#FF00_1234,Dest);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert instr.opcode == "MOV"
    assert instr.operands[0].value == "16#FF00_1234"
    assert instr.operands[1].value == "Dest"


def test_hex_literal_standard():
    result = parse("MOV(16#FF00,Dest);")
    rungs = result.unwrap()
    assert rungs[0].instructions[0].operands[0].value == "16#FF00"


def test_arithmetic_expression_operand():
    result = parse("CAL(Result,ValA * 100 + ValB);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert instr.opcode == "CAL"
    assert len(instr.operands) == 2
    assert instr.operands[0].value == "Result"
    assert instr.operands[1].value == "ValA * 100 + ValB"


def test_simple_expression_operand():
    result = parse("CAL(Sum,A + B);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert instr.operands[1].value == "A + B"


def test_cmp_instruction():
    result = parse("EQU(A,B);")
    rungs = result.unwrap()
    instr = rungs[0].instructions[0]
    assert instr.opcode == "EQU"
    assert len(instr.operands) == 2
    assert instr.operands[0].value == "A"
    assert instr.operands[1].value == "B"


def test_io_address_with_module_slot():
    result = parse("XIC(Rack:3:I.Data.2)OTE(Flag);")
    rungs = result.unwrap()
    assert rungs[0].instructions[0].operands[0].value == "Rack:3:I.Data.2"


def test_tag_with_colon_suffix_in_branch():
    result = parse("XIC(SignalA:SI)[XIO(B)]OTE(Flag);")
    rungs = result.unwrap()
    xic = rungs[0].instructions[0]
    assert xic.operands[0].value == "SignalA:SI"
    assert xic.branch is not None


# ---------------------------------------------------------------------------
# All Rockwell instruction types
# ---------------------------------------------------------------------------

class TestAllOpcodes:
    def test_bit_instructions(self):
        for opcode in ("XIC", "XIO", "OTE", "OTL", "OTU", "ONS", "OSR", "OSF"):
            result = parse(f"{opcode}(Tag);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_timer_instructions(self):
        for opcode in ("TON", "TOF", "RTO"):
            result = parse(f"{opcode}(T1,1000,0);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_counter_instructions(self):
        for opcode in ("CTU", "CTD", "CTUD"):
            result = parse(f"{opcode}(C1,10,0);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_reset_instruction(self):
        result = parse("RES(T1);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "RES"

    def test_compare_instructions(self):
        for opcode in ("EQU", "NEQ", "GRT", "LES", "GEQ", "LEQ", "LIMIT", "MEQ"):
            result = parse(f"{opcode}(A,B);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_math_instructions(self):
        for opcode in ("ADD", "SUB", "MUL", "DIV", "MOD", "SQRT", "NEG", "ABS"):
            result = parse(f"{opcode}(A,B,Dest);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_move_logical_instructions(self):
        for opcode in ("MOV", "MVM", "AND", "OR", "XOR", "NOT", "SWPB", "CLR", "BTD"):
            result = parse(f"{opcode}(A,B);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_shift_fill_instructions(self):
        for opcode in ("BSL", "BSR", "FLL", "LFL"):
            result = parse(f"{opcode}(A,B,C);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_sequencer_instructions(self):
        for opcode in ("SQI", "SQO"):
            result = parse(f"{opcode}(A,B,C);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_system_value_instructions(self):
        for opcode in ("GSV", "SSV"):
            result = parse(f"{opcode}(A,B,C,D);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_program_control_instructions(self):
        for opcode in ("JSR", "SBR", "RET", "JMP", "LBL", "MCR", "TND"):
            result = parse(f"{opcode}(Routine);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode

    def test_no_operand_instructions(self):
        for opcode in ("NOP", "TND", "AFI"):
            result = parse(f"{opcode};")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode
            assert rungs[0].instructions[0].operands == []

    def test_fault_instructions(self):
        for opcode in ("MSG", "FBC", "FSC"):
            result = parse(f"{opcode}(A,B);")
            rungs = result.unwrap()
            assert rungs[0].instructions[0].opcode == opcode


# ---------------------------------------------------------------------------
# Nested branches
# ---------------------------------------------------------------------------

class TestNestedBranches:
    def test_simple_parallel(self):
        result = parse("XIC(A)[XIO(B),XIO(C)]OTE(D);")
        rungs = result.unwrap()
        xic = rungs[0].instructions[0]
        assert xic.branch is not None
        assert len(xic.branch) == 2

    def test_nested_branch(self):
        result = parse("XIC(A)[XIO(B)XIC(C),XIO(D)]OTE(E);")
        rungs = result.unwrap()
        xic = rungs[0].instructions[0]
        assert xic.branch is not None
        assert len(xic.branch) == 2
        assert len(xic.branch[0]) == 2

    def test_deeply_nested_branch(self):
        result = parse("XIC(A)[XIO(B)XIC(C),XIO(D)XIC(E),XIO(F)XIC(G)]OTE(H);")
        rungs = result.unwrap()
        xic = rungs[0].instructions[0]
        assert xic.branch is not None
        assert len(xic.branch) == 3

    def test_multiple_instructions_in_branch_path(self):
        result = parse("XIC(A)[XIO(B)XIC(C),XIO(D)XIC(E)]OTE(F);")
        rungs = result.unwrap()
        branch = rungs[0].instructions[0].branch
        assert len(branch) == 2
        assert len(branch[0]) == 2
        assert len(branch[1]) == 2

    def test_empty_branch(self):
        result = parse("XIC(A)[]OTE(B);")
        rungs = result.unwrap()
        assert len(rungs[0].instructions) == 2

    def test_single_item_branch(self):
        result = parse("XIC(A)[XIO(B)]OTE(C);")
        rungs = result.unwrap()
        branch = rungs[0].instructions[0].branch
        assert branch is not None
        assert len(branch) == 1

    def test_output_branch(self):
        result = parse("XIC(A)OTE(B)[OTL(C)];")
        rungs = result.unwrap()
        ote = rungs[0].instructions[1]
        assert ote.branch is not None

    def test_multiple_output_branches(self):
        result = parse("XIC(A)OTE(B)[OTL(C)][OTU(D)];")
        rungs = result.unwrap()
        ote = rungs[0].instructions[1]
        assert ote.branch is not None


# ---------------------------------------------------------------------------
# Tag path edge cases
# ---------------------------------------------------------------------------

class TestTagPaths:
    def test_simple_tag(self):
        result = parse("XIC(Motor_Start);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "Motor_Start"

    def test_member_access(self):
        result = parse("XIC(Timer1.DN);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "Timer1.DN"

    def test_nested_member_access(self):
        result = parse("XIC(Motor.Config.Speed);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "Motor.Config.Speed"

    def test_array_index(self):
        result = parse("XIC(Arr[5]);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "Arr.5"

    def test_array_member(self):
        result = parse("XIC(Arr[2].Member);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "Arr.2.Member"

    def test_io_address_module_slot(self):
        result = parse("XIC(Rack:3:I.Data.2);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "Rack:3:I.Data.2"

    def test_io_address_suffix(self):
        result = parse("XIC(SignalA:SI);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "SignalA:SI"

    def test_controller_tag(self):
        result = parse("XIC(Controller.Tags.TagName);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "Controller.Tags.TagName"

    def test_program_tag(self):
        result = parse("XIC(Program:MainProgram.TagName);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "Program:MainProgram.TagName"


# ---------------------------------------------------------------------------
# Instruction operand variations
# ---------------------------------------------------------------------------

class TestInstructionOperands:
    def test_zero_operand_instruction(self):
        result = parse("AFI;")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands == []

    def test_one_operand(self):
        result = parse("JMP(Label);")
        rungs = result.unwrap()
        assert len(rungs[0].instructions[0].operands) == 1

    def test_two_operands(self):
        result = parse("MOV(42,Dest);")
        rungs = result.unwrap()
        assert len(rungs[0].instructions[0].operands) == 2

    def test_three_operands(self):
        result = parse("TON(T1,1000,0);")
        rungs = result.unwrap()
        assert len(rungs[0].instructions[0].operands) == 3

    def test_wildcard_operand(self):
        result = parse("TON(T1,?,?);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[1].value == "?"
        assert rungs[0].instructions[0].operands[2].value == "?"

    def test_hex_operand(self):
        result = parse("MOV(16#FF00,Dest);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "16#FF00"

    def test_hex_with_underscores(self):
        result = parse("MOV(16#FF_00_12_34,Dest);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "16#FF_00_12_34"

    def test_negative_number_operand(self):
        result = parse("MOV(-42,Dest);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "-42"

    def test_float_operand(self):
        result = parse("MOV(3.14,Dest);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "3.14"

    def test_expression_operand(self):
        result = parse("CPT(Dest,A+B*C);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[1].value == "A + B * C"

    def test_empty_operands_middle(self):
        result = parse("CAL(A,,B);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "A"
        assert rungs[0].instructions[0].operands[1].value == ""
        assert rungs[0].instructions[0].operands[2].value == "B"

    def test_empty_operands_trailing(self):
        result = parse("CAL(X,,);")
        rungs = result.unwrap()
        assert len(rungs[0].instructions[0].operands) == 3
        assert rungs[0].instructions[0].operands[2].value == ""


# ---------------------------------------------------------------------------
# Rung structure
# ---------------------------------------------------------------------------

class TestRungStructure:
    def test_single_rung(self):
        result = parse("XIC(A)OTE(B);")
        rungs = result.unwrap()
        assert len(rungs) == 1

    def test_multiple_rungs(self):
        result = parse("XIC(A)OTE(B);XIC(C)OTE(D);")
        rungs = result.unwrap()
        assert len(rungs) == 2

    def test_rung_numbering(self):
        result = parse("XIC(A);XIO(B);OTE(C);")
        rungs = result.unwrap()
        for i, r in enumerate(rungs):
            assert r.number == i

    def test_rung_without_semicolon(self):
        result = parse("XIC(A)OTE(B)")
        rungs = result.unwrap()
        assert len(rungs) == 1

    def test_empty_text(self):
        result = parse("")
        rungs = result.unwrap()
        assert rungs == []

    def test_whitespace_only(self):
        result = parse("   \n  \t  ")
        rungs = result.unwrap()
        assert rungs == []


# ---------------------------------------------------------------------------
# Realistic ladder logic patterns
# ---------------------------------------------------------------------------

class TestRealisticPatterns:
    def test_motor_start_stop(self):
        text = "XIC(Motor_Start)XIC(Safety_Ok)[XIO(E_Stop),XIC(Auto_Mode)]OTE(Motor_Run);"
        result = parse(text)
        rungs = result.unwrap()
        assert len(rungs) == 1
        assert len(rungs[0].instructions) == 3
        assert rungs[0].instructions[1].branch is not None

    def test_seal_in_circuit(self):
        text = "XIC(Start)[XIC(Motor),XIO(Stop)]OTE(Motor);"
        result = parse(text)
        rungs = result.unwrap()
        assert len(rungs) == 1
        branch = rungs[0].instructions[0].branch
        assert branch is not None
        assert len(branch) == 2

    def test_timer_rung(self):
        text = "XIC(Motor)TON(Timer1,5000,0);"
        result = parse(text)
        rungs = result.unwrap()
        assert len(rungs[0].instructions) == 2
        assert rungs[0].instructions[1].opcode == "TON"
        assert rungs[0].instructions[1].operands[0].value == "Timer1"

    def test_counter_rung(self):
        text = "XIC(Pulse)CTU(Counter1,10,0);"
        result = parse(text)
        rungs = result.unwrap()
        assert rungs[0].instructions[1].opcode == "CTU"

    def test_move_rung(self):
        text = "MOV(Source,Dest);"
        result = parse(text)
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "MOV"

    def test_compare_rung(self):
        text = "EQU(Source1,Source2);"
        result = parse(text)
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "EQU"

    def test_jsr_rung(self):
        text = "JSR(Subroutine,Param1,Param2);"
        result = parse(text)
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "JSR"
        assert len(rungs[0].instructions[0].operands) == 3

    def test_jmp_lbl_rung(self):
        text = "JMP(Label);"
        result = parse(text)
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "JMP"

    def test_multiple_outputs(self):
        text = "XIC(A)OTE(B)OTE(C);"
        result = parse(text)
        rungs = result.unwrap()
        assert len(rungs[0].instructions) == 3
        assert rungs[0].instructions[0].opcode == "XIC"
        assert rungs[0].instructions[1].opcode == "OTE"
        assert rungs[0].instructions[2].opcode == "OTE"

    def test_complex_branching(self):
        text = "XIC(A)[XIO(B)XIC(C),XIO(D)XIC(E),XIO(F)]OTE(G);"
        result = parse(text)
        rungs = result.unwrap()
        branch = rungs[0].instructions[0].branch
        assert branch is not None
        assert len(branch) == 3

    def test_latch_unlatch(self):
        text = "XIC(Start)OTL(Motor);XIC(Stop)OTU(Motor);"
        result = parse(text)
        rungs = result.unwrap()
        assert len(rungs) == 2
        assert rungs[0].instructions[1].opcode == "OTL"
        assert rungs[1].instructions[1].opcode == "OTU"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrorCases:
    def test_missing_closing_paren(self):
        result = parse("XIC(A")
        assert isinstance(result, Failure)

    def test_invalid_token(self):
        result = parse("@invalid!;")
        assert isinstance(result, Failure)


# ---------------------------------------------------------------------------
# CMP instruction with expression
# ---------------------------------------------------------------------------

class TestCmpInstruction:
    def test_cmp_with_expression(self):
        result = parse("CMP(A>B AND C<D);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "CMP"
        assert rungs[0].instructions[0].operands[0].value == "A > B AND C < D"

    def test_cmp_with_comparison(self):
        result = parse("CMP(Val > 100);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "CMP"
        assert "Val > 100" in rungs[0].instructions[0].operands[0].value

    def test_cmp_in_branch(self):
        result = parse("XIC(A)[CMP(X>0)]OTE(B);")
        rungs = result.unwrap()
        assert len(rungs[0].instructions) == 2
        assert rungs[0].instructions[0].branch is not None

    def test_cmp_with_nested_parentheses(self):
        result = parse("CMP(SQRT(SQRT(4)));")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "CMP"
        assert rungs[0].instructions[0].operands[0].value == "SQRT(SQRT(4))"

    def test_cmp_with_deeply_nested_parentheses(self):
        result = parse("CMP(((Tag_a*2)));")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "CMP"
        assert rungs[0].instructions[0].operands[0].value == "((Tag_a * 2))"

    def test_cmp_with_nested_math(self):
        result = parse("CMP(A * (B + (C / D)));")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].opcode == "CMP"
        assert rungs[0].instructions[0].operands[0].value == "A * (B + (C / D))"


# ---------------------------------------------------------------------------
# CPT with parenthesized expressions and function calls
# ---------------------------------------------------------------------------

class TestCptParenthesizedExpressions:
    def test_cpt_with_parenthesized_expression(self):
        result = parse("CPT(Dest, (A+B)*C);")
        rungs = result.unwrap()
        instr = rungs[0].instructions[0]
        assert instr.opcode == "CPT"
        assert instr.operands[0].value == "Dest"
        assert instr.operands[1].value == "(A + B) * C"

    def test_cpt_with_function_call(self):
        result = parse("CPT(Dest, SQRT(A));")
        rungs = result.unwrap()
        instr = rungs[0].instructions[0]
        assert instr.opcode == "CPT"
        assert instr.operands[0].value == "Dest"
        assert instr.operands[1].value == "SQRT(A)"

    def test_cpt_with_nested_function_call(self):
        result = parse("CPT(Dest, SQRT(SQRT(A)));")
        rungs = result.unwrap()
        instr = rungs[0].instructions[0]
        assert instr.opcode == "CPT"
        assert instr.operands[1].value == "SQRT(SQRT(A))"

    def test_cpt_with_abs_function(self):
        result = parse("CPT(Dest, ABS(A));")
        rungs = result.unwrap()
        instr = rungs[0].instructions[0]
        assert instr.opcode == "CPT"
        assert instr.operands[1].value == "ABS(A)"

    def test_cpt_with_multiple_parenthesized_groups(self):
        result = parse("CPT(Dest, (A+B) * (C-D));")
        rungs = result.unwrap()
        instr = rungs[0].instructions[0]
        assert instr.opcode == "CPT"
        assert instr.operands[1].value == "(A + B) * (C - D)"

    def test_cpt_with_parenthesized_leading_expression(self):
        result = parse("CPT(Dest, (A+B));")
        rungs = result.unwrap()
        instr = rungs[0].instructions[0]
        assert instr.opcode == "CPT"
        assert instr.operands[1].value == "(A + B)"

    def test_cpt_with_function_and_operators(self):
        result = parse("CPT(Dest, SQRT(A) * 2);")
        rungs = result.unwrap()
        instr = rungs[0].instructions[0]
        assert instr.opcode == "CPT"
        assert instr.operands[1].value == "SQRT(A) * 2"

    def test_mov_with_function_call(self):
        result = parse("MOV(SQRT(4), Dest);")
        rungs = result.unwrap()
        instr = rungs[0].instructions[0]
        assert instr.opcode == "MOV"
        assert instr.operands[0].value == "SQRT(4)"
        assert instr.operands[1].value == "Dest"

    def test_add_with_parenthesized_operand(self):
        result = parse("ADD((A + B), C, Dest);")
        rungs = result.unwrap()
        instr = rungs[0].instructions[0]
        assert instr.opcode == "ADD"
        assert instr.operands[0].value == "(A + B)"
        assert instr.operands[1].value == "C"
        assert instr.operands[2].value == "Dest"


# ---------------------------------------------------------------------------
# Unary prefix operators (NOT, !, -)
# ---------------------------------------------------------------------------

class TestUnaryOperators:
    def test_not_prefix(self):
        result = parse("CMP(NOT A);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "NOT A"

    def test_negate_prefix(self):
        result = parse("CPT(Dest, -A);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[1].value == "-A"

    def test_bang_prefix(self):
        result = parse("CPT(Dest, !A);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[1].value == "!A"

    def test_not_with_binary_operator(self):
        result = parse("CPT(Dest, NOT A AND B);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[1].value == "NOT A AND B"

    def test_negate_with_binary_operator(self):
        result = parse("CPT(Dest, A + -B);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[1].value == "A + -B"

    def test_negate_parenthesised(self):
        result = parse("CPT(Dest, -(A + B));")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[1].value == "-(A + B)"

    def test_negate_function_call(self):
        result = parse("CPT(Dest, -SQRT(A));")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[1].value == "-SQRT(A)"

    def test_not_with_comparison(self):
        result = parse("CMP(NOT A > B);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "NOT A > B"

    def test_not_does_not_consume_identifier(self):
        """NOT should not eat into a longer identifier like NOTIFY."""
        result = parse("XIC(NOTIFY)OTE(B);")
        rungs = result.unwrap()
        assert rungs[0].instructions[0].operands[0].value == "NOTIFY"


# ---------------------------------------------------------------------------
# Deeply nested branches (3+ levels)
# ---------------------------------------------------------------------------

class TestDeepNestedBranches:
    def test_three_way_parallel(self):
        result = parse("XIC(A)[XIO(B),XIO(C),XIO(D)]OTE(E);")
        rungs = result.unwrap()
        branch = rungs[0].instructions[0].branch
        assert branch is not None
        assert len(branch) == 3

    def test_nested_parallel_in_parallel(self):
        # Two-level: outer branch has 2 paths, each with 2 sub-paths
        result = parse("XIC(A)[XIO(B)XIC(C),XIO(D)XIC(E)]OTE(F);")
        rungs = result.unwrap()
        branch = rungs[0].instructions[0].branch
        assert branch is not None
        assert len(branch) == 2
        assert len(branch[0]) == 2
        assert len(branch[1]) == 2
