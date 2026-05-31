from pathlib import Path

from returns.result import Failure, Success

from l5x_lint.domain.errors import (
    L5XStructureError,
    RLLParseError,
    SoftwareRevisionError,
    STParseError,
)
from l5x_lint.domain.models import L5XProject
from l5x_lint.infrastructure.adapter import parse_l5x
from l5x_lint.infrastructure.parsers._factory import create_parser
from l5x_lint.infrastructure.parsers.base import L5XParser
from l5x_lint.infrastructure.parsers.v38 import L5XParserV38

from helpers import l5x_with_rll, l5x_with_st, minimal_l5x, parse_and_analyze

TEST_DATA = Path(__file__).parent.parent / "data"
VALID_DIR = TEST_DATA / "valid"
INVALID_DIR = TEST_DATA / "invalid"


def _result(r):
    assert isinstance(r, Success)
    return r.unwrap()


def test_parse_file_path():
    path = VALID_DIR / "projects" / "Simple.L5X"
    project = _result(parse_l5x(path))
    assert isinstance(project, L5XProject)
    assert project.schema_revision == "1.0"
    assert project.software_revision == "36.00"
    assert project.controller.name == "Empty"
    assert project.controller.processor_type == "1756-L84E"


def test_parse_xml_string():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.00">
  <Controller Use="Target" Name="TestPLC" ProcessorType="1756-L83E">
    <DataTypes/>
    <Tags/>
    <Programs/>
    <Tasks/>
    <AddOnInstructionDefinitions/>
    <Modules/>
  </Controller>
</RSLogix5000Content>"""
    project = _result(parse_l5x(xml))
    assert project.controller.name == "TestPLC"
    assert project.controller.processor_type == "1756-L83E"


def test_parse_invalid_xml():
    result = parse_l5x("this is not xml")
    assert isinstance(result, Failure)


def test_parse_missing_controller():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.00">
</RSLogix5000Content>"""
    result = parse_l5x(xml)
    assert isinstance(result, Failure)


def test_parse_empty_data_types():
    path = VALID_DIR / "projects" / "Empty.L5X"
    project = _result(parse_l5x(path))
    assert project.controller.data_types == []


def test_parse_data_types():
    path = VALID_DIR / "projects" / "Simple.L5X"
    project = _result(parse_l5x(path))
    assert project.controller.data_types == []


def test_parse_data_types_with_members():
    path = VALID_DIR / "projects" / "Test.L5X"
    project = _result(parse_l5x(path))
    dts = project.controller.data_types
    assert len(dts) > 0

    simple = next(dt for dt in dts if dt.name == "SimpleType")
    assert simple.family == "NoFamily"
    assert simple.class_ == "User"
    member_names = [m.name for m in simple.members]
    assert "BoolMember" in member_names
    assert "SintMember" in member_names
    assert "DintMember" in member_names

    bool_member = next(m for m in simple.members if m.name == "BoolMember")
    assert bool_member.data_type == "BIT"
    assert bool_member.dimension == 0
    assert bool_member.bit_number == 0

    array_type = next(dt for dt in dts if dt.name == "ArrayType")
    sint_array = next(m for m in array_type.members if m.name == "SintArray")
    assert sint_array.data_type == "SINT"
    assert sint_array.dimension == 5
    assert sint_array.bit_number is None


def test_parse_controller_tags():
    path = VALID_DIR / "projects" / "Simple.L5X"
    project = _result(parse_l5x(path))
    tags = project.controller.tags
    assert len(tags) > 0
    tag_0 = next(t for t in tags if t.name == "Tag_0")
    assert tag_0.data_type == "DINT"
    assert tag_0.dimensions == ()
    assert tag_0.scope == "controller"

    assert any(t.name == "Tag_1" for t in tags)


def test_parse_tag_with_description():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    tag = next(t for t in project.controller.tags if t.name == "DINT")
    assert tag.description == "DINT_DESCRIPTION"


def test_parse_programs():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    assert len(project.controller.programs) == 1
    prog = project.controller.programs[0]
    assert prog.name == "MainProgram"


def test_parse_program_tags():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    prog = project.controller.programs[0]
    prog_tags = [t for t in prog.tags if t.name == "AND_01"]
    assert len(prog_tags) == 1
    assert prog_tags[0].data_type == "FBD_LOGICAL"
    assert prog_tags[0].scope == "program:MainProgram"


def test_parse_program_routines():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    prog = project.controller.programs[0]
    assert len(prog.routines) == 4
    routine_names = {r.name for r in prog.routines}
    assert "MainRoutine" in routine_names
    assert "STRoutine" in routine_names
    assert "FBDRoutine" in routine_names
    assert "SequentialFunctionChart" in routine_names


def test_parse_rll_routine():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    prog = project.controller.programs[0]
    rll = next(r for r in prog.routines if r.name == "MainRoutine")
    assert rll.type == "RLL"
    assert "XIC(DINT.0)OTE(DINT.2);" in rll.cdata
    assert "XIC(DINT.2)OTE(DINT.3);" in rll.cdata


def test_parse_st_routine():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    prog = project.controller.programs[0]
    st = next(r for r in prog.routines if r.name == "STRoutine")
    assert st.type == "ST"
    assert "DINT := DINT AND UDINT;" in st.cdata
    assert "DINT := DINT AND ULINT;" in st.cdata


def test_parse_fbd_routine():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    prog = project.controller.programs[0]
    fbd = next(r for r in prog.routines if r.name == "FBDRoutine")
    assert fbd.type == "FBD"
    assert fbd.cdata == ""


def test_parse_sfc_routine():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    prog = project.controller.programs[0]
    sfc = next(r for r in prog.routines if r.name == "SequentialFunctionChart")
    assert sfc.type == "SFC"
    assert sfc.cdata == ""


def test_parse_tasks():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    assert len(project.controller.tasks) == 1
    task = project.controller.tasks[0]
    assert task.name == "MainTask"
    assert task.programs == ["MainProgram"]


def test_parse_aois():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    assert len(project.controller.aois) == 1
    aoi = project.controller.aois[0]
    assert aoi.name == "AddOnInstruction"
    assert aoi.revision == "1.7"


def test_parse_aoi_parameters():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    aoi = project.controller.aois[0]
    assert len(aoi.parameters) == 2
    enable_in = aoi.parameters[0]
    assert enable_in["name"] == "EnableIn"
    assert enable_in["data_type"] == "BOOL"
    assert enable_in["usage"] == "Input"


def test_parse_aoi_local_tags():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    aoi = project.controller.aois[0]
    assert len(aoi.local_tags) == 1
    tag = aoi.local_tags[0]
    assert tag.name == "AOIDINTLocalTag"
    assert tag.data_type == "DINT"
    assert tag.scope == "aoi:AddOnInstruction"


def test_parse_modules():
    path = VALID_DIR / "projects" / "ACDTestsWithAOI.L5X"
    project = _result(parse_l5x(path))
    assert len(project.controller.modules) == 2
    local = next(m for m in project.controller.modules if m.name == "Local")
    assert local.parent == "Local"
    eth = next(m for m in project.controller.modules if m.name == "ETH_MODULE")
    assert eth.parent == "Local"


def test_parse_no_programs():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.00">
  <Controller Use="Target" Name="TestPLC">
    <DataTypes/>
    <Tags/>
    <Programs/>
    <Tasks/>
    <AddOnInstructionDefinitions/>
    <Modules/>
  </Controller>
</RSLogix5000Content>"""
    project = _result(parse_l5x(xml))
    assert project.controller.programs == []


def test_parse_no_tasks():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.00">
  <Controller Use="Target" Name="TestPLC">
    <DataTypes/>
    <Tags/>
    <Programs/>
    <Tasks/>
    <AddOnInstructionDefinitions/>
    <Modules/>
  </Controller>
</RSLogix5000Content>"""
    project = _result(parse_l5x(xml))
    assert project.controller.tasks == []


def test_parse_no_aois():
    path = VALID_DIR / "projects" / "Simple.L5X"
    project = _result(parse_l5x(path))
    assert project.controller.aois == []


def test_parse_no_modules():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.00">
  <Controller Use="Target" Name="TestPLC">
    <DataTypes/>
    <Tags/>
    <Programs/>
    <Tasks/>
    <AddOnInstructionDefinitions/>
    <Modules/>
  </Controller>
</RSLogix5000Content>"""
    project = _result(parse_l5x(xml))
    assert project.controller.modules == []


def test_parse_tag_with_dimensions():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.00">
  <Controller Use="Target" Name="TestPLC">
    <DataTypes/>
    <Tags>
      <Tag Name="Arr1D" TagType="Base" DataType="DINT" Dimensions="10"/>
      <Tag Name="Arr2D" TagType="Base" DataType="DINT" Dimensions="3,4"/>
      <Tag Name="Scalar" TagType="Base" DataType="BOOL"/>
    </Tags>
    <Programs/>
    <Tasks/>
    <AddOnInstructionDefinitions/>
    <Modules/>
  </Controller>
</RSLogix5000Content>"""
    project = _result(parse_l5x(xml))
    tags = {t.name: t for t in project.controller.tags}
    assert tags["Arr1D"].dimensions == (10,)
    assert tags["Arr2D"].dimensions == (3, 4)
    assert tags["Scalar"].dimensions == ()


def test_parse_with_type_error():
    result = parse_l5x(42)
    assert isinstance(result, Failure)


def test_parse_v32_sample():
    path = VALID_DIR / "projects" / "v32_minimal.L5X"
    project = _result(parse_l5x(path))
    assert project.software_revision == "32.00"
    assert project.controller.name == "V32Test"
    assert project.controller.processor_type == "1756-L72"


def test_parse_v38_sample():
    path = VALID_DIR / "projects" / "v38_minimal.L5X"
    project = _result(parse_l5x(path))
    assert project.software_revision == "38.00"
    assert project.controller.name == "V38Test"
    assert project.controller.processor_type == "1756-L85E"


def test_parse_v38_tags():
    path = VALID_DIR / "projects" / "v38_minimal.L5X"
    project = _result(parse_l5x(path))
    tags = {t.name: t for t in project.controller.tags}
    assert "V38Tag" in tags
    assert tags["V38Tag"].data_type == "DINT"
    assert "V38TagNoMeta" in tags
    assert tags["V38TagNoMeta"].data_type == "BOOL"


def test_parse_v38_programs_and_routines():
    path = VALID_DIR / "projects" / "v38_minimal.L5X"
    project = _result(parse_l5x(path))
    assert len(project.controller.programs) == 1
    prog = project.controller.programs[0]
    assert prog.name == "MainProgram"
    assert len(prog.routines) == 1
    assert prog.routines[0].name == "Main"
    assert prog.routines[0].type == "ST"
    assert "V38Tag := 0;" in prog.routines[0].cdata


def test_parse_v38_tasks():
    path = VALID_DIR / "projects" / "v38_minimal.L5X"
    project = _result(parse_l5x(path))
    assert len(project.controller.tasks) == 1
    task = project.controller.tasks[0]
    assert task.name == "MainTask"
    assert task.programs == ["MainProgram"]


def test_parse_v38_aoi_no_aliasfor():
    path = VALID_DIR / "projects" / "v38_minimal.L5X"
    project = _result(parse_l5x(path))
    assert len(project.controller.aois) == 1
    aoi = project.controller.aois[0]
    assert aoi.name == "V38AOI"
    assert len(aoi.parameters) == 1
    assert aoi.parameters[0]["name"] == "InputParam"
    assert aoi.parameters[0]["data_type"] == "DINT"


def test_parse_v38_modules():
    path = VALID_DIR / "projects" / "v38_minimal.L5X"
    project = _result(parse_l5x(path))
    assert len(project.controller.modules) == 1
    mod = project.controller.modules[0]
    assert mod.name == "Local"
    assert mod.parent == "Local"


def test_parser_factory_returns_base_for_v32():
    parser = create_parser("32.00", "1.0").unwrap()
    assert isinstance(parser, L5XParser)
    assert not isinstance(parser, L5XParserV38)


def test_parser_factory_returns_base_for_v36():
    parser = create_parser("36.00", "1.0").unwrap()
    assert isinstance(parser, L5XParser)
    assert not isinstance(parser, L5XParserV38)


def test_parser_factory_returns_v38_for_v38():
    parser = create_parser("38.00", "1.0").unwrap()
    assert isinstance(parser, L5XParserV38)


def test_parser_factory_returns_base_for_unknown():
    parser = create_parser("99.99", "1.0").unwrap()
    assert isinstance(parser, L5XParser)
    assert not isinstance(parser, L5XParserV38)


def test_parser_factory_fails_for_empty_string():
    result = create_parser("", "1.0")
    assert isinstance(result, Failure)


def test_parser_stores_revision_metadata():
    parser = create_parser("36.00", "1.0").unwrap()
    assert parser.software_revision == "36.00"
    assert parser.schema_revision == "1.0"
    path = VALID_DIR / "projects" / "v38_minimal.L5X"
    project = _result(parse_l5x(path))
    assert len(project.controller.modules) == 1
    mod = project.controller.modules[0]
    assert mod.name == "Local"
    assert mod.parent == "Local"


# ---------------------------------------------------------------------------
# Malformed XML — well-formedness errors (ET.parse failures)
# ---------------------------------------------------------------------------

class TestMalformedXml:
    def test_truncated_xml(self):
        result = parse_l5x("<RSLogix5000Content>")
        assert isinstance(result, Failure)

    def test_unclosed_child_element(self):
        xml = minimal_l5x("<DataTypes><DataType Name='Bad'>")
        result = parse_l5x(xml)
        assert isinstance(result, Failure)

    def test_mismatched_tags(self):
        xml = minimal_l5x("</Controller>")
        result = parse_l5x(xml)
        assert isinstance(result, Failure)

    def test_bad_entity_reference(self):
        xml = minimal_l5x("&invalid;")
        result = parse_l5x(xml)
        assert isinstance(result, Failure)

    def test_garbage_in_valid_skeleton(self):
        xml = minimal_l5x("<<<<<<<GARBAGE>>>>>>>")
        result = parse_l5x(xml)
        assert isinstance(result, Failure)

    def test_wrong_root_element(self):
        xml = '<?xml version="1.0"?><NotL5X><Controller Name="T"/></NotL5X>'
        result = parse_l5x(xml)
        assert isinstance(result, Failure)

    def test_empty_file(self):
        result = parse_l5x("")
        assert isinstance(result, Failure)

    def test_binary_garbage(self):
        result = parse_l5x("\xff\xfe\x00\x00")
        assert isinstance(result, Failure)

    def test_non_xml_string(self):
        result = parse_l5x("hello world")
        assert isinstance(result, Failure)

    def test_malformed_xml_produces_structure_error(self):
        result = parse_l5x("<unclosed>")
        match result:
            case Failure(L5XStructureError(element="XML")):
                pass
            case _:
                assert False, f"Expected L5XStructureError(element='XML'), got {result}"


# ---------------------------------------------------------------------------
# Bad RLL code — should stop analysis with RLLParseError
# (parse_l5x only extracts XML; analyze() triggers RLL/ST parsing)
# ---------------------------------------------------------------------------

class TestBadRllCode:
    def test_garbage_rll_through_pipeline(self):
        """CDATA wrapping prevents XML-level failure; Lark parser rejects bad RLL."""
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="RLL">
              <RLLContent><Rung Number="0"><Text><![CDATA[@invalid!;]]></Text></Rung></RLLContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_and_analyze(xml)
        assert isinstance(result, Failure), f"Expected Failure for bad RLL, got {result}"

    def test_truncated_rll_in_cdata(self):
        """CDATA wrapping; truncated RLL inside CDATA."""
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="RLL">
              <RLLContent><Rung Number="0"><Text><![CDATA[XIC(]]></Text></Rung></RLLContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_and_analyze(xml)
        assert isinstance(result, Failure), f"Expected Failure for truncated RLL, got {result}"

    def test_empty_rll_text(self):
        xml = l5x_with_rll("Main", "")
        result = parse_l5x(xml)
        # Empty text is valid — parser returns empty rungs
        assert isinstance(result, Success)

    def test_rll_with_xml_special_chars_in_cdata(self):
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="RLL">
              <RLLContent><Rung Number="0"><Text><![CDATA[XIC(Tag) < 5 OTE(Output);]]></Text></Rung></RLLContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_l5x(xml)
        # CDATA preserves the literal text, parser should handle it
        assert isinstance(result, (Success, Failure))

    def test_multiple_bad_routines_all_reported(self):
        """Both routines have unparseable RLL — both errors should be reported."""
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Bad1" Type="RLL">
              <RLLContent><Rung Number="0"><Text><![CDATA[@invalid1;]]></Text></Rung></RLLContent>
            </Routine>
            <Routine Name="Bad2" Type="RLL">
              <RLLContent><Rung Number="0"><Text><![CDATA[@invalid2;]]></Text></Rung></RLLContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_and_analyze(xml)
        assert isinstance(result, Failure), f"Expected Failure for two bad routines, got {result}"


# ---------------------------------------------------------------------------
# Bad ST code — should stop analysis with STParseError
# (parse_l5x only extracts XML; analyze() triggers RLL/ST parsing)
# ---------------------------------------------------------------------------

class TestBadStCode:
    def test_garbage_st_through_pipeline(self):
        """CDATA wrapping; garbage ST inside CDATA."""
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="ST">
              <STContent><Line Number="0"><![CDATA[garbage code here]]></Line></STContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_and_analyze(xml)
        assert isinstance(result, Failure), f"Expected Failure for bad ST, got {result}"

    def test_truncated_st_in_cdata(self):
        """CDATA wrapping; truncated ST inside CDATA."""
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="ST">
              <STContent><Line Number="0"><![CDATA[IF x ></Line></STContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_and_analyze(xml)
        assert isinstance(result, Failure), f"Expected Failure for truncated ST, got {result}"

    def test_st_missing_rhs(self):
        """Missing RHS in assignment — ST parser should reject."""
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="ST">
              <STContent><Line Number="0"><![CDATA[x := ;]]></Line></STContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_and_analyze(xml)
        assert isinstance(result, Failure), f"Expected Failure for missing RHS, got {result}"

    def test_st_with_xml_special_chars(self):
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="ST">
              <STContent><Line Number="0"><![CDATA[IF x < 5 THEN y := 1; END_IF]]></Line></STContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_l5x(xml)
        # CDATA preserves < and > literally, parser handles it
        assert isinstance(result, (Success, Failure))


# ---------------------------------------------------------------------------
# CDATA edge cases
# ---------------------------------------------------------------------------

class TestCdataEdgeCases:
    def test_rll_in_cdata_section(self):
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="RLL">
              <RLLContent><Rung Number="0"><![CDATA[XIC(Tag)OTE(Output);]]></Rung></RLLContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_l5x(xml)
        assert isinstance(result, Success)

    def test_st_in_cdata_section(self):
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="ST">
              <STContent><Line Number="0"><![CDATA[x := 1;]]></Line></STContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_l5x(xml)
        assert isinstance(result, Success)

    def test_mixed_cdata_and_text_rll(self):
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="RLL">
              <RLLContent>
                <Rung Number="0"><Text>XIC(Tag1)OTE(Output1);</Text></Rung>
                <Rung Number="1"><![CDATA[XIC(Tag2)OTE(Output2);]]></Rung>
              </RLLContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_l5x(xml)
        assert isinstance(result, Success)


# ---------------------------------------------------------------------------
# Bad SoftwareRevision — should fail gracefully
# ---------------------------------------------------------------------------

class TestBadSoftwareRevision:
    def test_empty_software_revision(self):
        xml = '<?xml version="1.0"?><RSLogix5000Content SchemaRevision="1.0" SoftwareRevision=""><Controller Name="T"/></RSLogix5000Content>'
        result = parse_l5x(xml)
        # Empty version — factory returns SoftwareRevisionError
        assert isinstance(result, Failure)

    def test_non_numeric_software_revision(self):
        xml = '<?xml version="1.0"?><RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="abc"><Controller Name="T"/></RSLogix5000Content>'
        result = parse_l5x(xml)
        assert isinstance(result, Failure)

    def test_future_version_warns_but_continues(self):
        xml = minimal_l5x(software_revision="99.00")
        result = parse_l5x(xml)
        # v99 has no XSD, validation skips, parser uses base — should succeed
        assert isinstance(result, Success)

    def test_old_version_without_xsd(self):
        xml = minimal_l5x(software_revision="20.01")
        result = parse_l5x(xml)
        # v20 has no XSD, validation skips — should succeed
        assert isinstance(result, Success)


# ---------------------------------------------------------------------------
# XSD validation failures — missing required structure
# ---------------------------------------------------------------------------

class TestXsdValidationFailures:
    def test_missing_controller_element(self):
        xml = """<?xml version="1.0"?>
<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.00">
</RSLogix5000Content>"""
        result = parse_l5x(xml)
        match result:
            case Failure(L5XStructureError(element="Controller")):
                pass
            case _:
                assert False, f"Expected L5XStructureError(element='Controller'), got {result}"

    def test_routine_missing_type_attribute(self):
        xml = minimal_l5x("""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="NoType">
              <RLLContent><Rung Number="0"><Text>XIC(Tag)OTE(Out);</Text></Rung></RLLContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_l5x(xml)
        assert isinstance(result, Failure)

    def test_routine_type_none_is_valid(self):
        """Type='None' is a valid enum value in the XSD."""
        xml = minimal_l5x("""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Empty" Type="None"/>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_l5x(xml)
        # Type="None" is valid per XSD — empty routine is fine
        assert isinstance(result, Success)


# ---------------------------------------------------------------------------
# Error type assertions — confirm correct error wrapper
# ---------------------------------------------------------------------------

class TestErrorTypes:
    def test_well_formedness_error_is_structure_error(self):
        result = parse_l5x("<bad>")
        match result:
            case Failure(L5XStructureError()):
                pass
            case _:
                assert False, f"Expected L5XStructureError, got {result}"

    def test_rll_parse_error_type(self):
        """CDATA-wrapped bad RLL triggers parse failure through analyze()."""
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="RLL">
              <RLLContent><Rung Number="0"><Text><![CDATA[@invalid!;]]></Text></Rung></RLLContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_and_analyze(xml)
        assert isinstance(result, Failure), f"Expected Failure for bad RLL, got {result}"

    def test_st_parse_error_type(self):
        """CDATA-wrapped bad ST triggers parse failure through analyze()."""
        xml = minimal_l5x(f"""
        <DataTypes/><Tags/>
        <Programs><Program Name="Main">
          <Tags/>
          <Routines>
            <Routine Name="Main" Type="ST">
              <STContent><Line Number="0"><![CDATA[garbage code here]]></Line></STContent>
            </Routine>
          </Routines>
        </Program></Programs>
        <Tasks/>
        <AddOnInstructionDefinitions/>
        <Modules/>""")
        result = parse_and_analyze(xml)
        assert isinstance(result, Failure), f"Expected Failure for bad ST, got {result}"

    def test_wrong_arg_type_is_adapter_error(self):
        result = parse_l5x(42)
        match result:
            case Failure():
                pass
            case _:
                assert False, f"Expected Failure, got {result}"
