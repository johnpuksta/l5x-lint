"""Generate benchmark L5X files with realistic mixed content.

Run: python tests/data/benchmarks/generate.py
Creates 5 files: bench_100kb.L5X through bench_50mb.L5X
"""

from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def header():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.02" '
        'TargetType="Controller" ContainsContext="true" '
        'ExportDate="Sat Mar 04 21:40:05 2023" '
        'ExportOptions="References NoRawData L5KData DecoratedData Context">\n'
        '<Controller Name="BenchmarkCtrl">\n'
    )


def footer():
    return '</Controller>\n</RSLogix5000Content>\n'


def data_types_section():
    """User-defined data types."""
    return """\
<DataTypes Use="Context">
  <DataType Name="MotorParams" Family="NoFamily" Class="User">
    <Members>
      <Member Name="Speed" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
      <Member Name="Torque" DataType="REAL" Dimension="0" Radix="Float" Hidden="false" ExternalAccess="Read/Write"/>
      <Member Name="Running" DataType="BOOL" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
      <Member Name="FaultCode" DataType="SINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
    </Members>
  </DataType>
  <DataType Name="AlarmStruct" Family="NoFamily" Class="User">
    <Members>
      <Member Name="Active" DataType="BOOL" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
      <Member Name="Count" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
      <Member Name="Timestamp" DataType="DINT" Dimension="0" Radix="Decimal" Hidden="false" ExternalAccess="Read/Write"/>
    </Members>
  </DataType>
  <DataType Name="PIDparams" Family="NoFamily" Class="User">
    <Members>
      <Member Name="Setpoint" DataType="REAL" Dimension="0" Radix="Float" Hidden="false" ExternalAccess="Read/Write"/>
      <Member Name="Kp" DataType="REAL" Dimension="0" Radix="Float" Hidden="false" ExternalAccess="Read/Write"/>
      <Member Name="Ki" DataType="REAL" Dimension="0" Radix="Float" Hidden="false" ExternalAccess="Read/Write"/>
      <Member Name="Kd" DataType="REAL" Dimension="0" Radix="Float" Hidden="false" ExternalAccess="Read/Write"/>
      <Member Name="Output" DataType="REAL" Dimension="0" Radix="Float" Hidden="false" ExternalAccess="Read/Write"/>
    </Members>
  </DataType>
</DataTypes>
"""


def controller_tags_section(count):
    """Controller-scoped tags of various types."""
    tags = ['<Tags Use="Context">\n']
    for i in range(count):
        dtype = ["DINT", "BOOL", "REAL", "STRING", "SINT", "LINT"][i % 6]
        tags.append(
            f'<Tag Name="Ctrl{i}" TagType="Base" DataType="{dtype}" Radix="Decimal" '
            f'Constant="false" ExternalAccess="Read/Write">'
            f'<Data Format="Decorated"><DataValue DataType="{dtype}" Radix="Decimal" '
            f'Value="0"/></Data></Tag>\n'
        )
    # Array tags
    for i in range(max(count // 10, 1)):
        tags.append(
            f'<Tag Name="Arr{i}" TagType="Base" DataType="DINT" Radix="Decimal" '
            f'Constant="false" ExternalAccess="Read/Write" Dimensions="100">'
            f'<Data Format="Decorated"><Array DataType="DINT" Dimensions="100"/>'
            f'</Data></Tag>\n'
        )
    # UDT tags
    for i in range(max(count // 5, 1)):
        tags.append(
            f'<Tag Name="Motor{i}" TagType="Base" DataType="MotorParams" '
            f'Radix="NullType" Constant="false" ExternalAccess="Read/Write">\n'
            f'<Data Format="Decorated"><Structure DataType="MotorParams">'
            f'<DataValueMember Name="Speed" DataType="DINT" Value="0"/>'
            f'<DataValueMember Name="Torque" DataType="REAL" Value="0.0"/>'
            f'<DataValueMember Name="Running" DataType="BOOL" Value="0"/>'
            f'<DataValueMember Name="FaultCode" DataType="SINT" Value="0"/>'
            f'</Structure></Data></Tag>\n'
        )
    tags.append('</Tags>\n')
    return "".join(tags)


def aoi_section(count):
    """AddOn Instruction definitions."""
    aois = ['<AddOnInstructionDefinitions Use="Context">\n']
    for i in range(count):
        aois.append(f"""\
<AddOnInstructionDefinition Name="AOI_Motor{i}" Revision="1.0">
  <Parameters>
    <Parameter Name="EnableIn" TagType="Base" DataType="BOOL" Usage="Input" Radix="Decimal" Required="false" Visible="false" ExternalAccess="Read Only"/>
    <Parameter Name="EnableOut" TagType="Base" DataType="BOOL" Usage="Output" Radix="Decimal" Required="false" Visible="false" ExternalAccess="Read Only"/>
    <Parameter Name="SpeedRef" TagType="Base" DataType="DINT" Usage="Input" Radix="Decimal" Required="true" Visible="true" ExternalAccess="Read/Write"/>
    <Parameter Name="Running" TagType="Base" DataType="BOOL" Usage="Output" Radix="Decimal" Required="false" Visible="true" ExternalAccess="Read/Write"/>
  </Parameters>
  <LocalTags>
    <LocalTag Name="SpeedActual" DataType="DINT" Radix="Decimal" ExternalAccess="None"/>
  </LocalTags>
  <Routines>
    <Routine Name="Logic" Type="RLL">
      <RLLContent>
        <Rung Number="0" Type="N"><Text><![CDATA[XIC(EnableIn)OTE(Running);]]></Text></Rung>
        <Rung Number="1" Type="N"><Text><![CDATA[MOV(SpeedRef,SpeedActual);]]></Text></Rung>
      </RLLContent>
    </Routine>
  </Routines>
</AddOnInstructionDefinition>
""")
    aois.append('</AddOnInstructionDefinitions>\n')
    return "".join(aois)


def rll_rungs(count, tag_pool):
    """Generate RLL rung text."""
    rungs = []
    opcodes = [
        lambda t1, t2: f"XIC({t1})OTE({t2});",
        lambda t1, t2: f"XIO({t1})OTE({t2});",
        lambda t1, t2: f"XIC({t1})XIC({t2})OTE(Ctrl0);",
        lambda t1, t2: f"LES({t1},{t2})OTE(Ctrl0);",
        lambda t1, t2: f"GRT({t1},{t2})OTE(Ctrl1);",
        lambda t1, t2: f"EQU({t1},{t2})MOV({t1},Arr0[0]);",
        lambda t1, t2: f"NEQ({t1},{t2})ADD({t1},{t2},Ctrl0);",
        lambda t1, t2: f"XIC({t1})TON(Timer{i % 10},5000,0);",
        lambda t1, t2: f"XIC({t1})CTU(Counter{i % 10},{t2},100);",
        lambda t1, t2: f"COP({t1},{t2},10);",
    ]
    for i in range(count):
        t1 = f"Ctrl{i % tag_pool}"
        t2 = f"Ctrl{(i + 1) % tag_pool}"
        rungs.append(f'<Rung Number="{i}" Type="N"><Text><![CDATA[{opcodes[i % len(opcodes)](t1, t2)}]]></Text></Rung>\n')
    return "".join(rungs)


def st_body(count, tag_pool):
    """Generate ST statements."""
    parts = []
    for i in range(count):
        t = f"Ctrl{i % tag_pool}"
        patterns = [
            f"{t} := {t} + 1;",
            f"{t} := {t} * 2;",
            f"IF {t} > 0 THEN {t} := {t} - 1; END_IF",
            f"{t} := {t} OR Ctrl{(i + 1) % tag_pool};",
        ]
        parts.append(patterns[i % len(patterns)])
    return " ".join(parts)


def routine(name, rtype, content):
    """Wrap routine content in XML."""
    if rtype == "RLL":
        return f"""\
<Routine Name="{name}" Type="RLL">
<RLLContent>
{content}</RLLContent>
</Routine>
"""
    else:
        return f"""\
<Routine Name="{name}" Type="ST">
<STContent>
<![CDATA[{content}]]>
</STContent>
</Routine>
"""


def program(name, tags, routines):
    """Wrap program content."""
    return f"""\
<Program Name="{name}">
<Tags Use="Context">
{tags}</Tags>
<Routines Use="Context">
{routines}</Routines>
</Program>
"""


def build_benchmark(target_bytes, label):
    """Build a complete L5X file targeting approximately target_bytes."""
    # Scale parameters based on target size
    if target_bytes < 200_000:
        ctrl_tags = 30
        aoi_count = 2
        rungs = 50
        st_stmts = 30
        programs = 1
    elif target_bytes < 1_000_000:
        ctrl_tags = 100
        aoi_count = 5
        rungs = 300
        st_stmts = 100
        programs = 1
    elif target_bytes < 5_000_000:
        ctrl_tags = 300
        aoi_count = 10
        rungs = 2000
        st_stmts = 500
        programs = 2
    elif target_bytes < 20_000_000:
        ctrl_tags = 800
        aoi_count = 20
        rungs = 10000
        st_stmts = 2000
        programs = 3
    else:
        ctrl_tags = 2000
        aoi_count = 30
        rungs = 50000
        st_stmts = 5000
        programs = 5

    parts = [header()]
    parts.append(data_types_section())
    parts.append(controller_tags_section(ctrl_tags))
    parts.append(aoi_section(aoi_count))
    parts.append('<Programs Use="Context">\n')

    for p in range(programs):
        prog_name = f"Program{p}" if p > 0 else "MainProgram"
        prog_tags = controller_tags_section(max(ctrl_tags // programs // 2, 5))
        routines = []

        # Main RLL routine
        main_rll = rll_rungs(rungs // programs, ctrl_tags)
        routines.append(routine("Main", "RLL", main_rll))

        # Secondary RLL routine with different patterns
        if programs > 1 or target_bytes > 500_000:
            sec_rll = rll_rungs(max(rungs // programs // 2, 20), ctrl_tags)
            routines.append(routine("Control", "RLL", sec_rll))

        # ST routine
        st_code = st_body(st_stmts // programs, ctrl_tags)
        routines.append(routine("STLogic", "ST", st_code))

        parts.append(program(prog_name, prog_tags, "".join(routines)))

    parts.append('</Programs>\n')
    parts.append(footer())

    content = "".join(parts)
    actual_size = len(content.encode("utf-8"))

    # Pad if needed by adding more rungs to MainProgram
    if actual_size < target_bytes:
        deficit = target_bytes - actual_size
        extra_rungs_needed = deficit // 120  # ~120 bytes per rung
        extra_rll = rll_rungs(extra_rungs_needed, ctrl_tags)
        # Insert before the closing </Routines> of MainProgram
        marker = '</Routines>\n</Program>\n</Programs>'
        insert_routine = routine("Extra", "RLL", extra_rll)
        content = content.replace(
            marker,
            insert_routine + marker,
            1,
        )

    actual_size = len(content.encode("utf-8"))
    print(f"  {label}: {actual_size / 1024:.0f} KB ({actual_size / (1024*1024):.1f} MB)")
    return content


def main():
    configs = [
        ("bench_100kb.L5X", 100_000, "100KB"),
        ("bench_500kb.L5X", 500_000, "500KB"),
        ("bench_2mb.L5X", 2_000_000, "2MB"),
        ("bench_10mb.L5X", 10_000_000, "10MB"),
        ("bench_50mb.L5X", 50_000_000, "50MB"),
    ]

    print("Generating benchmark L5X files:")
    for filename, target, label in configs:
        content = build_benchmark(target, label)
        path = OUTPUT_DIR / filename
        path.write_text(content, encoding="utf-8")
        actual = path.stat().st_size
        print(f"    -> {path.name}: {actual / 1024:.0f} KB")

    print("Done.")


if __name__ == "__main__":
    main()
