import importlib

from l5x_lint.checks.cross import ec015_invalid_data_type
from l5x_lint.domain.models import Location, Routine, Tag
from l5x_lint.pipeline.symbols import SymbolTable


def _reset():
    importlib.reload(ec015_invalid_data_type)


def test_builtin_type_no_diagnostic():
    _reset()
    symbols = SymbolTable(controller_tags={"X": Tag(name="X", data_type="DINT")})
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ec015_invalid_data_type.ec015_invalid_data_type(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_undefined_type_emits_ec015():
    _reset()
    symbols = SymbolTable(
        controller_tags={"X": Tag(name="X", data_type="NonExistentType")}
    )
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ec015_invalid_data_type.ec015_invalid_data_type(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 1
    assert diags[0].code == "EC015"


def test_user_defined_type_no_diagnostic():
    _reset()
    from l5x_lint.domain.models import DataType

    symbols = SymbolTable(
        controller_tags={"X": Tag(name="X", data_type="MyType")},
        data_types={"MyType": DataType(name="MyType", family="", class_="")},
    )
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ec015_invalid_data_type.ec015_invalid_data_type(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []


def test_program_tag_undefined_type():
    _reset()
    symbols = SymbolTable(
        program_tags={"Prog": {"Y": Tag(name="Y", data_type="BadType")}},
    )
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ec015_invalid_data_type.ec015_invalid_data_type(
        r,
        symbols,
        Location(program="Prog", routine="Test"),
    )
    assert len(diags) == 1


def test_no_duplicate_reports():
    _reset()
    symbols = SymbolTable(
        controller_tags={
            "A": Tag(name="A", data_type="BadType"),
            "B": Tag(name="B", data_type="BadType"),
        }
    )
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ec015_invalid_data_type.ec015_invalid_data_type(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert len(diags) == 2


def test_empty_data_type_skipped():
    _reset()
    symbols = SymbolTable(controller_tags={"X": Tag(name="X", data_type="")})
    r = Routine(name="Test", type="RLL", rll_rungs=[])
    diags = ec015_invalid_data_type.ec015_invalid_data_type(
        r,
        symbols,
        Location(program="P", routine="Test"),
    )
    assert diags == []
