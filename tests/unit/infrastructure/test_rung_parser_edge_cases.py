"""Tests for RLL (Relay Ladder Logic) parser edge cases and features.

Covers: all opcode types, nested branches, multi-dimensional arrays,
IO addresses, expressions, and realistic ladder logic patterns.
"""

from returns.result import Failure

from infrastructure.rung_parser import parse

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
        # Nested branch with instruction before it in same path
        result = parse("XIC(A)[XIO(B)XIC(C),XIO(D)]OTE(E);")
        rungs = result.unwrap()
        xic = rungs[0].instructions[0]
        assert xic.branch is not None
        assert len(xic.branch) == 2
        # First path has 2 instructions
        assert len(xic.branch[0]) == 2

    def test_deeply_nested_branch(self):
        # Three-way parallel with instructions in each path
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
        assert len(branch[0]) == 2  # XIO(B) and XIC(C)
        assert len(branch[1]) == 2  # XIO(D) and XIC(E)

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
        assert rungs[0].instructions[0].operands[1].value == "A+B*C"

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
        # 3 instructions: XIC, XIC (with branch), OTE
        assert len(rungs[0].instructions) == 3
        assert rungs[0].instructions[1].branch is not None

    def test_seal_in_circuit(self):
        # Parallel branch with self-reference
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
