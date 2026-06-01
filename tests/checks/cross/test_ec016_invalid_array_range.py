import importlib

from l5x_lint.checks.cross import ec016_invalid_array_range
from l5x_lint.domain.models import Location, Routine, Tag
from l5x_lint.domain.symbols import SymbolTable


def _reset():
    importlib.reload(ec016_invalid_array_range)


def test_valid_dimensions_no_diagnostic():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "Arr": Tag(name="Arr", data_type="DINT", dimensions=(5,)),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec016_invalid_array_range.ec016_invalid_array_range(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_zero_dimension_emits_ec016():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "Bad": Tag(name="Bad", data_type="DINT", dimensions=(0,)),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec016_invalid_array_range.ec016_invalid_array_range(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
    assert diags[0].code == "EC016"
    assert "0" in diags[0].message


def test_negative_dimension_emits_ec016():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "Bad": Tag(name="Bad", data_type="DINT", dimensions=(-1,)),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec016_invalid_array_range.ec016_invalid_array_range(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1


def test_multi_dim_first_invalid():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "M": Tag(name="M", data_type="DINT", dimensions=(0, 5)),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec016_invalid_array_range.ec016_invalid_array_range(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1


def test_no_dimensions_no_diagnostic():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "X": Tag(name="X", data_type="DINT", dimensions=()),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec016_invalid_array_range.ec016_invalid_array_range(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_program_tag():
    _reset()
    symbols = SymbolTable(
        program_tags={
            "ProgA": {"Bad": Tag(name="Bad", data_type="DINT", dimensions=(0,))},
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    diags = ec016_invalid_array_range.ec016_invalid_array_range(
        r,
        symbols,
        Location(program="ProgA", routine="Test"),
    )
    assert len(diags) == 1
    assert diags[0].location.program == "ProgA"


def test_duplicate_reported_once():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "X": Tag(name="X", data_type="DINT", dimensions=(0,)),
        }
    )
    r = Routine(name="Test", type="ST", st_body=None)
    ec016_invalid_array_range.ec016_invalid_array_range(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    diags2 = ec016_invalid_array_range.ec016_invalid_array_range(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags2 == []
