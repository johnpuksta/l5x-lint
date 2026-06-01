import importlib

from l5x_lint.checks.cross import ec014_unresolved_constant
from l5x_lint.domain.models import Location, Routine, Tag
from l5x_lint.domain.symbols import SymbolTable


def _reset():
    importlib.reload(ec014_unresolved_constant)


def test_constant_with_initial_value_no_diagnostic():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "MYCONST": Tag(
                name="MYCONST", data_type="DINT", constant=True, has_initial_value=True
            ),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec014_unresolved_constant.ec014_unresolved_constant(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_constant_without_initial_value_emits_ec014():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "MYCONST": Tag(
                name="MYCONST", data_type="DINT", constant=True, has_initial_value=False
            ),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec014_unresolved_constant.ec014_unresolved_constant(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
    assert diags[0].code == "EC014"
    assert "MYCONST" in diags[0].message


def test_constant_without_init_emits_for_program_tag():
    _reset()
    symbols = SymbolTable(
        program_tags={
            "ProgA": {
                "Y": Tag(
                    name="Y", data_type="DINT", constant=True, has_initial_value=False
                )
            },
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec014_unresolved_constant.ec014_unresolved_constant(
        r,
        symbols,
        Location(program="ProgA", routine="Test"),
    )
    assert len(diags) == 1
    assert diags[0].location.program == "ProgA"


def test_non_constant_no_diagnostic():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "X": Tag(
                name="X", data_type="DINT", constant=False, has_initial_value=False
            ),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec014_unresolved_constant.ec014_unresolved_constant(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_multiple_constants():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "A": Tag(
                name="A", data_type="DINT", constant=True, has_initial_value=False
            ),
            "B": Tag(name="B", data_type="DINT", constant=True, has_initial_value=True),
            "C": Tag(
                name="C", data_type="DINT", constant=True, has_initial_value=False
            ),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec014_unresolved_constant.ec014_unresolved_constant(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 2


def test_no_duplicate_reports():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "X": Tag(
                name="X", data_type="DINT", constant=True, has_initial_value=False
            ),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec014_unresolved_constant.ec014_unresolved_constant(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
    diags2 = ec014_unresolved_constant.ec014_unresolved_constant(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags2 == []
