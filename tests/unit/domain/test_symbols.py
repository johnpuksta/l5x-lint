from returns.maybe import Nothing, Some

from domain.models import AOI, Controller, DataType, Member, Program, Tag
from domain.symbols import build_symbol_table


def test_empty_controller():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    assert table.controller_tags == {}
    assert table.program_tags == {}
    assert table.aoi_tags == {}
    assert table.data_types == {}


def test_controller_tags():
    c = Controller(
        name="Test",
        tags=[Tag(name="MyTag", data_type="DINT")],
    )
    table = build_symbol_table(c)
    assert "MyTag" in table.controller_tags
    assert table.controller_tags["MyTag"].data_type == "DINT"


def test_program_tags():
    c = Controller(
        name="Test",
        programs=[
            Program(
                name="MainProgram",
                tags=[
                    Tag(name="LocalTag", data_type="BOOL", scope="program:MainProgram"),
                ],
            ),
        ],
    )
    table = build_symbol_table(c)
    assert "MainProgram" in table.program_tags
    assert "LocalTag" in table.program_tags["MainProgram"]


def test_aoi_local_tags():
    c = Controller(
        name="Test",
        aois=[
            AOI(
                name="MyAOI",
                local_tags=[Tag(name="AOILocal", data_type="DINT", scope="aoi:MyAOI")],
            ),
        ],
    )
    table = build_symbol_table(c)
    assert "MyAOI" in table.aoi_tags
    assert "AOILocal" in table.aoi_tags["MyAOI"]


def test_data_types():
    c = Controller(
        name="Test",
        data_types=[DataType(name="MyType", family="NoFamily", class_="")],
    )
    table = build_symbol_table(c)
    assert "MyType" in table.data_types


def test_resolve_controller_tag():
    c = Controller(name="Test", tags=[Tag(name="MyTag", data_type="DINT")])
    table = build_symbol_table(c)
    result = table.resolve("MyTag")
    assert result == Some(Tag(name="MyTag", data_type="DINT"))


def test_resolve_program_tag():
    c = Controller(
        name="Test",
        programs=[
            Program(name="Prog", tags=[Tag(name="PTag", data_type="BOOL")]),
        ],
    )
    table = build_symbol_table(c)
    result = table.resolve("PTag", program="Prog")
    assert result == Some(Tag(name="PTag", data_type="BOOL"))


def test_resolve_program_overrides_controller():
    c = Controller(
        name="Test",
        tags=[Tag(name="Shared", data_type="DINT")],
        programs=[
            Program(name="Prog", tags=[Tag(name="Shared", data_type="BOOL")]),
        ],
    )
    table = build_symbol_table(c)
    result = table.resolve("Shared", program="Prog")
    assert result == Some(Tag(name="Shared", data_type="BOOL"))


def test_resolve_unknown():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    assert table.resolve("NonExistent") is Nothing


def test_resolve_without_program_gets_controller():
    c = Controller(name="Test", tags=[Tag(name="CTag", data_type="DINT")])
    table = build_symbol_table(c)
    result = table.resolve("CTag")
    assert result == Some(Tag(name="CTag", data_type="DINT"))


def test_multiple_programs():
    c = Controller(
        name="Test",
        programs=[
            Program(name="A", tags=[Tag(name="ATag", data_type="DINT")]),
            Program(name="B", tags=[Tag(name="BTag", data_type="BOOL")]),
        ],
    )
    table = build_symbol_table(c)
    assert "ATag" in table.program_tags["A"]
    assert "BTag" in table.program_tags["B"]
    assert table.resolve("ATag", program="A") is not Nothing
    assert table.resolve("BTag", program="B") is not Nothing
    assert table.resolve("ATag", program="B") is Nothing


def test_resolve_type_simple():
    c = Controller(
        name="Test",
        tags=[Tag(name="MyTag", data_type="DINT")],
        data_types=[DataType(name="DINT", family="NoFamily", class_="")],
    )
    table = build_symbol_table(c)
    dt = table.resolve_type("MyTag")
    assert dt is not None
    assert dt.name == "DINT"


def test_resolve_type_udt():
    c = Controller(
        name="Test",
        tags=[Tag(name="MyTag", data_type="MyType")],
        data_types=[
            DataType(
                name="MyType",
                family="NoFamily",
                class_="",
                members=[Member(name="FieldA", data_type="DINT")],
            ),
            DataType(name="DINT", family="NoFamily", class_=""),
        ],
    )
    table = build_symbol_table(c)
    dt = table.resolve_type("MyTag")
    assert dt is not None
    assert dt.name == "MyType"


def test_resolve_type_unknown_tag():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    assert table.resolve_type("NonExistent") is None


def test_resolve_type_unknown_data_type():
    c = Controller(
        name="Test",
        tags=[Tag(name="MyTag", data_type="NonExistentType")],
    )
    table = build_symbol_table(c)
    assert table.resolve_type("MyTag") is None


def test_resolve_member_type_found():
    c = Controller(
        name="Test",
        data_types=[
            DataType(
                name="MyType",
                family="NoFamily",
                class_="",
                members=[Member(name="FieldA", data_type="DINT")],
            ),
            DataType(name="DINT", family="NoFamily", class_=""),
        ],
    )
    table = build_symbol_table(c)
    dt = table.resolve_member_type("MyType", "FieldA")
    assert dt is not None
    assert dt.name == "DINT"


def test_resolve_member_type_not_found():
    c = Controller(
        name="Test",
        data_types=[
            DataType(
                name="MyType",
                family="NoFamily",
                class_="",
                members=[Member(name="FieldA", data_type="DINT")],
            ),
        ],
    )
    table = build_symbol_table(c)
    assert table.resolve_member_type("MyType", "NonExistent") is None


def test_resolve_member_type_unknown_base():
    c = Controller(name="Test")
    table = build_symbol_table(c)
    assert table.resolve_member_type("UnknownType", "Field") is None
