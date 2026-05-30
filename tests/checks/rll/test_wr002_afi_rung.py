from l5x_lint.checks.rll.wr002_afi_rung import wr002_afi_rung
from l5x_lint.domain.models import Controller, Location, Program, Routine
from l5x_lint.domain.rll_models import Instruction, Operand, ParsedRung
from l5x_lint.domain.st_models import StProgram
from l5x_lint.pipeline import analyze
from l5x_lint.pipeline.symbols import build_symbol_table


def _reset_registry():
    analyze._registry.clear()


def _loc(program="Prog", routine="Main", rung=None):
    return Location(program=program, routine=routine, rung=rung)


def _rung(*instructions):
    return ParsedRung(number=0, text="", instructions=list(instructions))


def _inst(opcode, *operand_values):
    return Instruction(
        opcode=opcode, operands=[Operand(value=v) for v in operand_values]
    )


def test_afi_first_instruction():
    r = Routine(
        name="Main", type="RLL",
        rll_rungs=[
            _rung(Instruction(opcode="AFI")),
            _rung(_inst("XIC", "TagA")),
        ],
    )
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = wr002_afi_rung(r, table, loc)
    assert len(result) == 1
    d = result[0]
    assert d.code == "WR002"
    assert d.severity == "warning"
    assert d.location.rung == 0


def test_no_afi():
    r = Routine(
        name="Main", type="RLL",
        rll_rungs=[_rung(_inst("XIC", "TagA"))],
    )
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = wr002_afi_rung(r, table, loc)
    assert result == []


def test_afi_not_first_instruction():
    r = Routine(
        name="Main", type="RLL",
        rll_rungs=[_rung(
            _inst("XIC", "TagA"),
            Instruction(opcode="AFI"),
        )],
    )
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = wr002_afi_rung(r, table, loc)
    assert result == []


def test_afi_multiple_rungs():
    rungs = [
        ParsedRung(number=0, text="", instructions=[Instruction(opcode="AFI")]),
        ParsedRung(
            number=1, text="",
            instructions=[_inst("XIC", "TagA")],
        ),
        ParsedRung(number=2, text="", instructions=[Instruction(opcode="AFI")]),
    ]
    r = Routine(name="Main", type="RLL", rll_rungs=rungs)
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = wr002_afi_rung(r, table, loc)
    assert len(result) == 2
    assert result[0].location.rung == 0
    assert result[1].location.rung == 2


def test_afi_st_ignored():
    r = Routine(name="Main", type="ST", st_body=StProgram(statements=[]))
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = wr002_afi_rung(r, table, loc)
    assert result == []


def test_afi_in_branch_not_flagged():
    branch_inst = Instruction(opcode="AFI")
    main_inst = Instruction(opcode="BST", branch=[[branch_inst]])
    r = Routine(name="Main", type="RLL", rll_rungs=[_rung(main_inst)])
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = wr002_afi_rung(r, table, loc)
    assert result == []


def test_afi_with_operands():
    r = Routine(
        name="Main", type="RLL",
        rll_rungs=[_rung(Instruction(opcode="AFI", operands=[Operand(value="X")]))],
    )
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = wr002_afi_rung(r, table, loc)
    assert len(result) == 1


def test_empty_routine():
    r = Routine(name="Main", type="RLL", rll_rungs=[])
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = wr002_afi_rung(r, table, loc)
    assert result == []


def test_wr002_via_analyze_pipeline():
    _reset_registry()
    analyze.register(wr002_afi_rung)

    rung0 = ParsedRung(number=0, text="", instructions=[Instruction(opcode="AFI")])
    rung1 = ParsedRung(
        number=1, text="",
        instructions=[_inst("XIC", "TagA")],
    )
    controller = Controller(
        name="Test",
        programs=[Program(
            name="Prog",
            routines=[Routine(name="Main", type="RLL", rll_rungs=[rung0, rung1])],
        )],
    )

    result = analyze.analyze(controller)
    ar = result.unwrap()
    assert ar.passed  # warnings only → still passes
    assert ar.warning_count == 1
    assert ar.diagnostics[0].code == "WR002"


def test_afi_non_rll_ignored():
    r = Routine(name="Main", type="FBD")
    controller = Controller(name="Test")
    table = build_symbol_table(controller)
    loc = _loc()
    result = wr002_afi_rung(r, table, loc)
    assert result == []
