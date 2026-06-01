from l5x_lint.checks.st.es002_duplicate_case_value import es002_duplicate_case_value
from l5x_lint.domain.models import Location, Routine, TagPath, TagPathSegment
from l5x_lint.domain.st_models import StCase, StLiteral, StProgram, StTagRef
from l5x_lint.domain.symbols import SymbolTable


def test_unique_case_values_no_diagnostic():
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StCase(
                    expression=StTagRef(
                        path=TagPath(segments=[TagPathSegment(name="x")])
                    ),
                    cases=[
                        ([StLiteral(value=1)], []),
                        ([StLiteral(value=2)], []),
                    ],
                ),
            ]
        ),
    )
    diags = es002_duplicate_case_value(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_duplicate_case_value_emits_es002():
    r = Routine(
        name="Test",
        type="ST",
        st_body=StProgram(
            statements=[
                StCase(
                    expression=StTagRef(
                        path=TagPath(segments=[TagPathSegment(name="x")])
                    ),
                    cases=[
                        ([StLiteral(value=1)], []),
                        ([StLiteral(value=1)], []),
                    ],
                    line=5,
                ),
            ]
        ),
    )
    diags = es002_duplicate_case_value(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert len(diags) == 1
    assert diags[0].code == "ES002"


def test_no_body():
    r = Routine(name="Test", type="ST", st_body=None)
    diags = es002_duplicate_case_value(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []


def test_non_st_ignored():
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = es002_duplicate_case_value(
        r, SymbolTable(), Location(program="P", routine="Test")
    )
    assert diags == []
