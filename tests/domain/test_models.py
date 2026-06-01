from returns.maybe import Some

from l5x_lint.domain.models import (
    Controller,
    DataType,
    L5XProject,
    Location,
    Member,
    Program,
    Routine,
    Tag,
    TagPath,
    TagPathSegment,
)


def test_tag_path_segment_simple():
    seg = TagPathSegment("Motor")
    assert seg.name == "Motor"
    assert seg.index is None
    assert seg.path_str() == "Motor"


def test_tag_path_segment_with_index():
    seg = TagPathSegment("Arr", 5)
    assert seg.name == "Arr"
    assert seg.index == 5
    assert seg.path_str() == "Arr[5]"


def test_tag_path_full_name():
    path = TagPath(
        [
            TagPathSegment("Conveyor"),
            TagPathSegment("Motor", 3),
            TagPathSegment("Speed"),
        ]
    )
    assert path.full_name == "Conveyor.Motor[3].Speed"


def test_tag_path_single_segment():
    path = TagPath([TagPathSegment("Motor_Run")])
    assert path.full_name == "Motor_Run"


def test_tag_path_empty_segments():
    path = TagPath([])
    assert path.full_name == ""


def test_location_minimal():
    loc = Location("MainProgram", "MainRoutine")
    assert loc.program == "MainProgram"
    assert loc.routine == "MainRoutine"
    assert loc.rung is None
    assert loc.line is None


def test_location_with_rung():
    loc = Location("MainProgram", "MainRoutine", rung=4)
    assert loc.rung == 4
    assert loc.line is None


def test_location_with_line():
    loc = Location("MainProgram", "MainRoutine", line=12)
    assert loc.rung is None
    assert loc.line == 12


def test_member_minimal():
    m = Member("Value", "DINT")
    assert m.name == "Value"
    assert m.data_type == "DINT"
    assert m.dimension == 0
    assert m.bit_number is None


def test_member_with_bit():
    m = Member("Status", "BOOL", bit_number=3)
    assert m.bit_number == 3


def test_data_type_no_members():
    dt = DataType("DINT", "NoFamily", "ProductDefined")
    assert dt.name == "DINT"
    assert dt.members == []


def test_data_type_with_members():
    dt = DataType(
        "TIMER",
        "NoFamily",
        "ProductDefined",
        members=[
            Member("PRE", "DINT"),
            Member("ACC", "DINT"),
        ],
    )
    assert len(dt.members) == 2
    assert dt.members[0].name == "PRE"


def test_data_type_user_defined():
    dt = DataType(
        "MyUDT",
        "NoFamily",
        "User",
        members=[
            Member("Speed", "REAL"),
            Member("Enabled", "BOOL"),
        ],
    )
    assert dt.class_ == "User"


def test_tag_defaults():
    tag = Tag("Motor_Run", "BOOL")
    assert tag.name == "Motor_Run"
    assert tag.data_type == "BOOL"
    assert tag.dimensions == ()
    assert tag.scope == "controller"
    assert tag.description == ""


def test_tag_with_dimensions():
    tag = Tag("MyArray", "DINT", dimensions=(10,))
    assert tag.dimensions == (10,)


def test_tag_program_scoped():
    tag = Tag("LocalTag", "BOOL", scope="program:MainProgram")
    assert tag.scope == "program:MainProgram"


def test_routine_rll():
    r = Routine("MainRoutine", "RLL")
    assert r.name == "MainRoutine"
    assert r.type == "RLL"
    assert r.rll_rungs == []
    assert r.st_body is None


def test_routine_st():
    r = Routine("StRoutine", "ST", st_body=Some(object()))
    assert r.type == "ST"
    assert r.st_body is not None


def test_program_empty():
    p = Program("MainProgram")
    assert p.name == "MainProgram"
    assert p.tags == []
    assert p.routines == []


def test_program_with_routines():
    r = Routine("MainRoutine", "RLL")
    p = Program("MainProgram", routines=[r])
    assert len(p.routines) == 1


def test_l5x_project():
    ctrl = Controller("MyPLC", processor_type="1756-L83E")
    project = L5XProject("v32", "32.01", ctrl)
    assert project.schema_revision == "v32"
    assert project.controller.name == "MyPLC"


def test_controller_with_tags():
    tags = [Tag("MyTag", "DINT"), Tag("MyBool", "BOOL")]
    ctrl = Controller("MyPLC", tags=tags)
    assert len(ctrl.tags) == 2
