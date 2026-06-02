import importlib

from domain.checks.cross import ec017_constant_modification
from domain.models import Location, Routine, Tag, TagPath, TagPathSegment
from domain.st_models import StAssignment, StLiteral, StProgram, StTagRef
from domain.symbols import SymbolTable


def _reset():
    importlib.reload(ec017_constant_modification)


def _make_st_routine(body_stmts) -> Routine:
    return Routine(name="Test", type="ST", st_body=StProgram(statements=body_stmts))


def _make_tag_ref(name: str) -> StTagRef:
    return StTagRef(path=TagPath(segments=[TagPathSegment(name=name)]))


def test_st_assign_to_constant_emits_ec017():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "MYCONST": Tag(name="MYCONST", data_type="DINT", constant=True)
        }
    )
    r = _make_st_routine(
        [
            StAssignment(
                target=TagPath(segments=[TagPathSegment(name="MYCONST")]),
                expression=StLiteral(value=5),
            ),
        ]
    )
    diags = ec017_constant_modification.ec017_constant_modification(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
    assert diags[0].code == "EC017"


def test_st_assign_to_non_constant_no_diagnostic():
    _reset()
    symbols = SymbolTable(
        controller_tags={"X": Tag(name="X", data_type="DINT", constant=False)}
    )
    r = _make_st_routine(
        [
            StAssignment(
                target=TagPath(segments=[TagPathSegment(name="X")]),
                expression=StLiteral(value=5),
            ),
        ]
    )
    diags = ec017_constant_modification.ec017_constant_modification(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_rll_ote_constant_emits_ec017():
    _reset()
    from domain.rll_models import Instruction, Operand, ParsedRung

    symbols = SymbolTable(
        controller_tags={
            "MYCONST": Tag(name="MYCONST", data_type="DINT", constant=True)
        }
    )
    r = Routine(
        name="Test",
        type="RLL",
        rll_rungs=[
            ParsedRung(
                number=1,
                text="",
                instructions=[
                    Instruction(opcode="OTE", operands=[Operand(value="MYCONST")]),
                ],
            ),
        ],
    )
    diags = ec017_constant_modification.ec017_constant_modification(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
    assert diags[0].code == "EC017"


def test_no_constant_tags_no_diagnostic():
    _reset()
    symbols = SymbolTable(controller_tags={"X": Tag(name="X", data_type="DINT")})
    r = _make_st_routine(
        [
            StAssignment(
                target=TagPath(segments=[TagPathSegment(name="X")]),
                expression=StLiteral(value=5),
            ),
        ]
    )
    diags = ec017_constant_modification.ec017_constant_modification(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []
