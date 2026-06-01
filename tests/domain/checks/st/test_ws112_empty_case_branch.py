from l5x_lint.domain.checks.st.ws112_empty_case_branch import ws112_empty_case_branch
from l5x_lint.domain.models import Location, Routine
from l5x_lint.domain.st_models import StCase, StLiteral, StProgram
from l5x_lint.domain.symbols import SymbolTable


def _make_routine(stmts) -> Routine:
    return Routine(name="Test", type="ST", st_body=StProgram(statements=stmts))


def test_case_all_branches_filled_no_diagnostic():
    r = _make_routine(
        [
            StCase(
                expression=StLiteral(value=1),
                cases=[
                    ([StLiteral(value=1)], [StLiteral(value=42)]),
                ],
                else_body=[StLiteral(value=0)],
                line=1,
            ),
        ]
    )
    diags = ws112_empty_case_branch(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_case_empty_branch_emits_ws112():
    r = _make_routine(
        [
            StCase(
                expression=StLiteral(value=1),
                cases=[
                    ([StLiteral(value=1)], []),
                ],
                else_body=[],
                line=5,
            ),
        ]
    )
    diags = ws112_empty_case_branch(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "WS112"
    assert diags[0].location.line == 5


def test_case_multiple_branches_one_empty():
    r = _make_routine(
        [
            StCase(
                expression=StLiteral(value=1),
                cases=[
                    ([StLiteral(value=1)], [StLiteral(value=10)]),
                    ([StLiteral(value=2)], []),
                    ([StLiteral(value=3)], [StLiteral(value=30)]),
                ],
                else_body=[StLiteral(value=0)],
                line=10,
            ),
        ]
    )
    diags = ws112_empty_case_branch(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1


def test_case_all_empty_branches():
    r = _make_routine(
        [
            StCase(
                expression=StLiteral(value=1),
                cases=[
                    ([StLiteral(value=1)], []),
                    ([StLiteral(value=2)], []),
                ],
                else_body=[],
                line=15,
            ),
        ]
    )
    diags = ws112_empty_case_branch(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 2


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ws112_empty_case_branch(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []
