from l5x_lint.checks.st.es003_for_bounds import es003_for_bounds
from l5x_lint.domain.models import Location, Routine, TagPath, TagPathSegment
from l5x_lint.domain.st_models import StFor, StLiteral, StProgram
from l5x_lint.pipeline.symbols import SymbolTable


def _make_routine(stmts) -> Routine:
    return Routine(name="Test", type="ST", st_body=StProgram(statements=stmts))


def test_for_within_range_no_diagnostic():
    r = _make_routine([
        StFor(
            variable=_tp("i"),
            start=StLiteral(value=0),
            end=StLiteral(value=100),
            body=[],
            line=1,
        ),
    ])
    diags = es003_for_bounds(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_for_end_exceeds_dint_max_emits_es003():
    r = _make_routine([
        StFor(
            variable=_tp("i"),
            start=StLiteral(value=0),
            end=StLiteral(value=9_999_999_999),
            body=[],
            line=5,
        ),
    ])
    diags = es003_for_bounds(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "ES003"
    assert "9,999,999,999" in diags[0].message or "9999999999" in diags[0].message
    assert diags[0].location.line == 5


def test_for_start_below_dint_min_emits_es003():
    r = _make_routine([
        StFor(
            variable=_tp("i"),
            start=StLiteral(value=-9_999_999_999_999),
            end=StLiteral(value=0),
            body=[],
            line=10,
        ),
    ])
    diags = es003_for_bounds(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1
    assert diags[0].code == "ES003"


def test_for_step_out_of_range():
    r = _make_routine([
        StFor(
            variable=_tp("i"),
            start=StLiteral(value=0),
            end=StLiteral(value=10),
            step=StLiteral(value=9_999_999_999_999),
            body=[],
            line=15,
        ),
    ])
    diags = es003_for_bounds(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1


def test_for_float_bounds_out_of_range():
    r = _make_routine([
        StFor(
            variable=_tp("i"),
            start=StLiteral(value=0.0),
            end=StLiteral(value=1e40),
            body=[],
            line=20,
        ),
    ])
    diags = es003_for_bounds(r, SymbolTable(), Location(program="P", routine="Test"))
    assert len(diags) == 1


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = es003_for_bounds(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def test_no_body_no_diagnostic():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = es003_for_bounds(r, SymbolTable(), Location(program="P", routine="Test"))
    assert diags == []


def _tp(name: str) -> TagPath:
    return TagPath(segments=[TagPathSegment(name=name)])
