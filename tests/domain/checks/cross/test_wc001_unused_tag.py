from l5x_lint.domain.checks.cross.wc001_unused_tag import _reset, wc001_unused_tag
from l5x_lint.domain.models import Controller, Location, Program, Routine, Tag
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.application import analyze
from l5x_lint.domain.symbols import build_symbol_table


def _reset_registry():
    analyze._registry.clear()
    _reset()


def _loc(program="Prog", routine="Main", rung=None):
    return Location(program=program, routine=routine, rung=rung)


def _rung(*instructions):
    return ParsedRung(number=0, text="", instructions=list(instructions))


def _inst(opcode, *operand_values):
    return Instruction(
        opcode=opcode, operands=[Operand(value=v) for v in operand_values]
    )


def test_used_controller_tag_no_diagnostic():
    _reset()
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "MyTag"))])
    c = Controller(name="Test", tags=[Tag(name="MyTag", data_type="DINT")])
    table = build_symbol_table(c)
    result = wc001_unused_tag(r, table, _loc())
    assert result == []


def test_unused_controller_tag_emits_wc001():
    _reset()
    r = Routine(name="Main", type="RLL", rll_rungs=[])
    c = Controller(name="Test", tags=[Tag(name="UnusedTag", data_type="DINT")])
    table = build_symbol_table(c)
    result = wc001_unused_tag(r, table, _loc())
    assert len(result) == 1
    assert result[0].code == "WC001"


def test_used_program_tag_no_diagnostic():
    _reset()
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(_inst("XIC", "ProgTag"))])
    c = Controller(
        name="Test",
        programs=[
            Program(name="Prog", tags=[Tag(name="ProgTag", data_type="DINT")]),
        ],
    )
    table = build_symbol_table(c)
    result = wc001_unused_tag(r, table, _loc(program="Prog"))
    assert result == []


def test_st_routine():
    _reset()
    from l5x_lint.domain.models import TagPath, TagPathSegment
    from l5x_lint.domain.st_models import StAssignment, StProgram, StTagRef

    prog = StProgram(
        statements=[
            StAssignment(
                target=TagPath(segments=[TagPathSegment(name="Out")]),
                expression=StTagRef(path=TagPath(segments=[TagPathSegment(name="In")])),
            ),
        ]
    )
    r = Routine(name="Main", type="ST", st_body=prog)
    c = Controller(
        name="Test",
        tags=[
            Tag(name="Out", data_type="DINT"),
            Tag(name="In", data_type="DINT"),
        ],
    )
    table = build_symbol_table(c)
    result = wc001_unused_tag(r, table, _loc())
    assert result == []
