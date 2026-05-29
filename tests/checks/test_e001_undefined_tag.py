from l5x_lint.checks._codes import E001
from l5x_lint.checks.e001_undefined_tag import (
    _check_rll,
    _check_st,
    _extract_base,
    e001_undefined_tag,
)
from l5x_lint.domain.models import (
    Controller,
    Location,
    Program,
    Routine,
    Tag,
    TagPath,
    TagPathSegment,
)
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.domain.st_models import (
    StAssignment,
    StBinaryOp,
    StCall,
    StFor,
    StIf,
    StJsr,
    StLiteral,
    StProgram,
    StTagRef,
    StWhile,
)
from l5x_lint.pipeline import analyze
from l5x_lint.pipeline.symbols import build_symbol_table


def _reset_registry():
    analyze._registry.clear()


def _loc(program="Prog", routine="Main", rung=None):
    return Location(program=program, routine=routine, rung=rung)


# -- _extract_base unit tests --


def test_extract_base_simple_tag():
    assert _extract_base("MyTag") == "MyTag"


def test_extract_base_member_access():
    assert _extract_base("MyTag.Member") == "MyTag"


def test_extract_base_array_access():
    assert _extract_base("MyTag[0]") == "MyTag"


def test_extract_base_array_member():
    assert _extract_base("MyTag[0].Member") == "MyTag"


def test_extract_base_hardware_tag():
    assert _extract_base("Local:1:I.Data") == "Local:1:I"


def test_extract_base_number():
    assert _extract_base("10000") is None


def test_extract_base_float():
    assert _extract_base("3.14") is None


def test_extract_base_negative():
    assert _extract_base("-42") is None


def test_extract_base_wildcard():
    assert _extract_base("?") is None


def test_extract_base_true():
    assert _extract_base("true") is None


def test_extract_base_false():
    assert _extract_base("FALSE") is None


def test_extract_base_string():
    assert _extract_base('"hello"') is None


def test_extract_base_empty():
    assert _extract_base("") is None


def test_extract_base_whitespace():
    assert _extract_base("  ") is None


# -- RLL E001 tests --


def _rung(*instructions):
    return ParsedRung(number=0, text="", instructions=list(instructions))


def _rungs(*rungs_list):
    return list(rungs_list)


def _rll_routine(name, rungs_list):
    return Routine(name=name, type="RLL", rll_rungs=rungs_list)


def _st_routine(name, st_body):
    return Routine(name=name, type="ST", st_body=st_body)


def _inst(opcode, *operand_values):
    return Instruction(
        opcode=opcode, operands=[Operand(value=v) for v in operand_values]
    )


def test_rll_known_tag_no_diagnostic():
    r = _rll_routine("Main", _rungs(_rung(_inst("XIC", "MyTag"))))
    controller = Controller(name="Test", tags=[Tag(name="MyTag", data_type="DINT")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert result == []


def test_rll_unknown_tag_emits_e001():
    r = _rll_routine("Main", _rungs(_rung(_inst("XIC", "NoSuchTag"))))
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert len(result) == 1
    d = result[0]
    assert d.code == "E001"
    assert d.severity == "error"
    assert d.message == E001(name="NoSuchTag").message
    assert d.location.rung == 0


def test_rll_mixed_known_unknown():
    r = _rll_routine("Main", _rungs(_rung(_inst("XIC", "GoodTag", "BadTag"))))
    controller = Controller(name="Test", tags=[Tag(name="GoodTag", data_type="DINT")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert len(result) == 1
    assert result[0].message == E001(name="BadTag").message


def test_rll_jsr_skips_first_operand():
    jsr = Instruction(
        opcode="JSR",
        operands=[Operand(value="RoutineName"), Operand(value="ParamTag")],
    )
    r = _rll_routine("Main", _rungs(_rung(jsr)))
    controller = Controller(name="Test", tags=[Tag(name="ParamTag", data_type="DINT")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert result == []


def test_rll_jsr_unknown_param_emits_e001():
    jsr = Instruction(
        opcode="JSR",
        operands=[Operand(value="RoutineName"), Operand(value="MissingParam")],
    )
    r = _rll_routine("Main", _rungs(_rung(jsr)))
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert len(result) == 1
    assert result[0].message == E001(name="MissingParam").message


def test_rll_numeric_literal_skipped():
    r = _rll_routine("Main", _rungs(_rung(_inst("TON", "Timer0", "10000"))))
    controller = Controller(name="Test", tags=[Tag(name="Timer0", data_type="TIMER")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert result == []


def test_rll_wildcard_skipped():
    r = _rll_routine("Main", _rungs(_rung(_inst("XIC", "?"))))
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert result == []


def test_rll_empty_rungs():
    r = _rll_routine("Main", [])
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert result == []


def test_rll_branches_checked():
    branch_inst = Instruction(opcode="XIC", operands=[Operand(value="BranchTag")])
    branch_inst2 = Instruction(opcode="XIC", operands=[Operand(value="NoTag")])
    main_inst = Instruction(opcode="BST", branch=[[branch_inst], [branch_inst2]])
    r = _rll_routine("Main", _rungs(_rung(main_inst)))
    controller = Controller(name="Test", tags=[Tag(name="BranchTag", data_type="DINT")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert len(result) == 1
    assert result[0].message == E001(name="NoTag").message


def test_rll_member_access_known_base():
    r = _rll_routine("Main", _rungs(_rung(_inst("XIC", "MyTag.Member"))))
    controller = Controller(name="Test", tags=[Tag(name="MyTag", data_type="MyUDT")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert result == []


def test_rll_member_access_unknown_base():
    r = _rll_routine("Main", _rungs(_rung(_inst("XIC", "NoTag.SomeMember"))))
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert len(result) == 1
    assert result[0].message == E001(name="NoTag").message


def test_rll_program_scope_overrides_controller():
    r = _rll_routine("Main", _rungs(_rung(_inst("XIC", "SharedName"))))
    controller = Controller(
        name="Test",
        tags=[Tag(name="SharedName", data_type="DINT")],
        programs=[Program(
            name="Prog", tags=[Tag(name="SharedName", data_type="BOOL")],
        )],
    )
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert result == []


def test_rll_multiple_rungs():
    rungs_list = [
        ParsedRung(
            number=0, text="",
            instructions=[_inst("XIC", "TagA")],
        ),
        ParsedRung(
            number=1, text="",
            instructions=[_inst("XIC", "TagB", "Missing")],
        ),
    ]
    r = _rll_routine("Main", rungs_list)
    controller = Controller(
        name="Test",
        tags=[Tag(name="TagA", data_type="DINT"), Tag(name="TagB", data_type="DINT")],
    )
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert len(result) == 1
    assert result[0].message == E001(name="Missing").message
    assert result[0].location.rung == 1


# -- ST E001 tests --


def test_st_known_tag_no_diagnostic():
    prog = StProgram(statements=[
        StAssignment(
            target=TagPath(segments=[TagPathSegment(name="Out")]),
            expression=StTagRef(path=TagPath(segments=[TagPathSegment(name="In")])),
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(
        name="Test",
        tags=[Tag(name="Out", data_type="DINT"), Tag(name="In", data_type="DINT")],
    )
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert result == []


def test_st_unknown_tag_emits_e001():
    prog = StProgram(statements=[
        StAssignment(
            target=TagPath(segments=[TagPathSegment(name="Out")]),
            expression=StTagRef(path=TagPath(segments=[TagPathSegment(name="MissingIn")])),
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(name="Test", tags=[Tag(name="Out", data_type="DINT")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert len(result) == 1
    assert result[0].message == E001(name="MissingIn").message


def test_st_target_unknown():
    prog = StProgram(statements=[
        StAssignment(
            target=TagPath(segments=[TagPathSegment(name="UndefTarget")]),
            expression=StLiteral(value=1),
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert len(result) == 1
    assert result[0].message == E001(name="UndefTarget").message


def test_st_if_condition_tags():
    prog = StProgram(statements=[
        StIf(
            condition=StTagRef(path=TagPath(segments=[TagPathSegment(name="Cond")])),
            body=[
                StAssignment(
                    target=TagPath(segments=[TagPathSegment(name="ThenTag")]),
                    expression=StLiteral(value=0),
                ),
            ],
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(
        name="Test",
        tags=[
            Tag(name="Cond", data_type="BOOL"),
            Tag(name="ThenTag", data_type="DINT"),
        ],
    )
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert result == []


def test_st_if_unknown_condition():
    prog = StProgram(statements=[
        StIf(
            condition=StTagRef(path=TagPath(segments=[TagPathSegment(name="NoCond")])),
            body=[],
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert len(result) == 1


def test_st_binary_op_tags():
    prog = StProgram(statements=[
        StAssignment(
            target=TagPath(segments=[TagPathSegment(name="Result")]),
            expression=StBinaryOp(
                left=StTagRef(path=TagPath(segments=[TagPathSegment(name="A")])),
                op="+",
                right=StTagRef(path=TagPath(segments=[TagPathSegment(name="MissingB")])),
            ),
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(
        name="Test",
        tags=[Tag(name="Result", data_type="DINT"), Tag(name="A", data_type="DINT")],
    )
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert len(result) == 1
    assert result[0].message == E001(name="MissingB").message


def test_st_while():
    prog = StProgram(statements=[
        StWhile(
            condition=StTagRef(path=TagPath(segments=[TagPathSegment(name="Flag")])),
            body=[
                StAssignment(
                    target=TagPath(segments=[TagPathSegment(name="Counter")]),
                    expression=StBinaryOp(
                        left=StTagRef(path=TagPath(segments=[TagPathSegment(name="Counter")])),
                        op="+",
                        right=StLiteral(value=1),
                    ),
                ),
            ],
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(
        name="Test",
        tags=[
            Tag(name="Flag", data_type="BOOL"),
            Tag(name="Counter", data_type="DINT"),
        ],
    )
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert result == []


def test_st_for():
    prog = StProgram(statements=[
        StFor(
            variable=TagPath(segments=[TagPathSegment(name="i")]),
            start=StLiteral(value=0),
            end=StLiteral(value=10),
            step=None,
            body=[],
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(name="Test", tags=[Tag(name="i", data_type="DINT")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert result == []


def test_st_for_with_exprs():
    prog = StProgram(statements=[
        StFor(
            variable=TagPath(segments=[TagPathSegment(name="LoopVar")]),
            start=StTagRef(path=TagPath(segments=[TagPathSegment(name="StartVal")])),
            end=StTagRef(path=TagPath(segments=[TagPathSegment(name="EndVal")])),
            step=StTagRef(path=TagPath(segments=[TagPathSegment(name="StepVal")])),
            body=[],
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(name="Test", tags=[
        Tag(name="LoopVar", data_type="DINT"),
        Tag(name="StartVal", data_type="DINT"),
        Tag(name="EndVal", data_type="DINT"),
        Tag(name="StepVal", data_type="DINT"),
    ])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert result == []


def test_st_call_args():
    prog = StProgram(statements=[
        StCall(
            name="TON",
            args=[
                StTagRef(path=TagPath(segments=[TagPathSegment(name="Timer0")])),
                StLiteral(value=10000),
                StLiteral(value=0),
            ],
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(name="Test", tags=[Tag(name="Timer0", data_type="TIMER")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert result == []


def test_st_call_unknown_arg():
    prog = StProgram(statements=[
        StCall(
            name="TON",
            args=[
                StTagRef(path=TagPath(segments=[TagPathSegment(name="MissingTimer")])),
            ],
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert len(result) == 1


def test_st_empty_program():
    r = _st_routine("Main", StProgram(statements=[]))
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert result == []


def test_st_none_body():
    r = _st_routine("Main", None)
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert result == []


# -- Full pipeline tests --


def test_e001_via_analyze_pipeline():
    _reset_registry()
    analyze.register(e001_undefined_tag)
    rung = ParsedRung(
        number=0, text="",
        instructions=[_inst("XIC", "Good", "Bad")],
    )
    controller = Controller(
        name="Test",
        tags=[Tag(name="Good", data_type="DINT")],
        programs=[Program(
            name="Prog",
            routines=[Routine(name="Main", type="RLL", rll_rungs=[rung])],
        )],
    )
    result = analyze.analyze(controller)
    ar = result.unwrap()
    assert not ar.passed
    assert ar.error_count == 1
    assert ar.diagnostics[0].code == "E001"


def test_e001_no_duplicates_for_same_tag():
    _reset_registry()
    analyze.register(e001_undefined_tag)
    rung = ParsedRung(
        number=0, text="",
        instructions=[_inst("XIC", "Missing", "Missing")],
    )
    controller = Controller(
        name="Test",
        programs=[Program(
            name="Prog",
            routines=[Routine(name="Main", type="RLL", rll_rungs=[rung])],
        )],
    )
    result = analyze.analyze(controller)
    ar = result.unwrap()
    assert ar.error_count == 2


def test_rll_non_rll_routine_ignored():
    r = Routine(name="Main", type="FBD")
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_rll(r, table, loc)
    assert result == []
    result_st = _check_st(r, table, loc)
    assert result_st == []


def test_st_jsr_args():
    prog = StProgram(statements=[
        StJsr(
            routine_name="SubRoutine",
            args=[StTagRef(path=TagPath(segments=[TagPathSegment(name="Arg1")]))],
        ),
    ])
    r = _st_routine("Main", prog)
    controller = Controller(name="Test", tags=[Tag(name="Arg1", data_type="DINT")])
    table = build_symbol_table(controller)
    loc = _loc()
    result = _check_st(r, table, loc)
    assert result == []
