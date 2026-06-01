from domain.errors import (
    AdapterArgumentError,
    L5XStructureError,
    RLLParseError,
    STParseError,
    SymbolTableError,
    UnsupportedRoutineError,
)


def test_adapter_argument_error():
    e = AdapterArgumentError(got="missing arg")
    assert "missing arg" in str(e)


def test_l5x_structure_error():
    e = L5XStructureError(element="Controller", detail="bad xml")
    assert "bad xml" in str(e)


def test_rll_parse_error():
    e = RLLParseError("rung1", "no match")
    assert "rung1" in str(e)
    assert "no match" in str(e)


def test_st_parse_error():
    e = STParseError("stmt1", 5)
    assert "stmt1" in str(e)
    assert "5" in str(e)


def test_symbol_table_error():
    e = SymbolTableError(detail="dup tag")
    assert "dup tag" in str(e)


def test_unsupported_routine_error():
    e = UnsupportedRoutineError(routine_name="Main", routine_type="FBD")
    assert "FBD" in str(e)
