"""Generate invalid L5X test data for all checks. One run produces all files."""

XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


def _ctrl(name="TestController"):
    return f'<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.02" TargetType="Controller" ContainsContext="true" ExportDate="Sat Mar 04 21:40:05 2023" ExportOptions="References NoRawData L5KData DecoratedData Context">\n<Controller Use="Context" Name="{name}">\n'


def _closer():
    return "</Controller>\n</RSLogix5000Content>\n"


def _tag(name, dtype="DINT", is_const="false", dims=None, value=None, no_data=False):
    dim_attr = f' Dimensions="{dims}"' if dims else ""
    data = (
        ""
        if no_data
        else f'<Data Format="Decorated"><DataValue DataType="{dtype}" Radix="Decimal" Value="{value or "0"}"/></Data>'
    )
    return f'<Tag Name="{name}" TagType="Base" DataType="{dtype}" Radix="Decimal" Constant="{is_const}" ExternalAccess="Read/Write"{dim_attr}>{data}</Tag>\n'


def _array_tag(name, dtype="DINT", dims=5, count=3, val=0):
    elems = "".join(
        f'<Element Index="{i}"><DataValue DataType="{dtype}" Radix="Decimal" Value="{val}"/></Element>'
        for i in range(count)
    )
    return f'<Tag Name="{name}" TagType="Base" DataType="{dtype}" Radix="Decimal" Constant="false" ExternalAccess="Read/Write" Dimensions="{dims}"><Data Format="Decorated"><Array DataType="{dtype}" Dimensions="{dims}">{elems}</Array></Data></Tag>\n'


def _aoi(name):
    return f'<AddOnInstructionDefinition Name="{name}" Revision="1.0"><Parameters/><LocalTags/></AddOnInstructionDefinition>\n'


def _prog(name, tags="", routines=""):
    return f'<Program Use="Context" Name="{name}">\n<Tags Use="Context">\n{tags}</Tags>\n<Routines Use="Context">\n{routines}</Routines>\n</Program>\n'


def _rll_routine(name="Main", rungs=""):
    return f'<Routine Use="Context" Name="{name}" Type="RLL">\n<RLLContent Use="Context">\n{rungs}</RLLContent>\n</Routine>\n'


def _st_routine(name="Main", cdata=""):
    return f'<Routine Use="Context" Name="{name}" Type="ST">\n<STContent Use="Context">\n<![CDATA[{cdata}]]>\n</STContent>\n</Routine>\n'


def _rung(num, text):
    return f'<Rung Use="Target" Number="{num}" Type="N">\n<Text><![CDATA[{text}]]></Text>\n</Rung>\n'


def _empty_routine(name="Main", rtype="RLL"):
    return f'<Routine Use="Context" Name="{name}" Type="{rtype}">\n</Routine>\n'


def write(
    code,
    controller_tags="",
    prog_tags="",
    routines="",
    data_types="",
    aois="",
    extra="",
):
    body = XML_HEADER + _ctrl()
    body += f'<DataTypes Use="Context">{data_types}</DataTypes>\n'
    body += f'<Tags Use="Context">{controller_tags}</Tags>\n'
    body += f'<Programs Use="Context">{_prog("MainProgram", prog_tags, routines)}</Programs>\n'
    if aois:
        body += f'<AddOnInstructionDefinitions Use="Context">{aois}</AddOnInstructionDefinitions>\n'
    body += _closer()
    path = f"tests/data/invalid/{code}.L5X"
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"{code}: {len(body)} bytes")


# ── CROSS CHECKS ──────────────────────────────────────────────

# EC011: AOI named TON (reserved name)
write(
    "EC011_reserved_name",
    aois=_aoi("TON"),
    routines=_rll_routine(rungs=_rung(0, "XIC(SomeTag)OTE(OutTag);")),
    controller_tags=_tag("SomeTag", "BOOL") + _tag("OutTag", "BOOL"),
)

# EC012: Array with fewer init elements than dimensions
write(
    "EC012_array_init_count",
    controller_tags=_array_tag("MyArr", "DINT", 5, 3),
    routines=_rll_routine(rungs=_rung(0, "XIC(SomeTag)OTE(OutTag);")),
    prog_tags=_tag("SomeTag", "BOOL") + _tag("OutTag", "BOOL"),
)

# EC013: Two LBL instructions with same name
write(
    "EC013_duplicate_jmp_label",
    routines=_rll_routine(rungs=_rung(0, "LBL(Mark);") + _rung(1, "LBL(Mark);")),
)

# EC014: CONSTANT tag without Data element (no initial value)
write(
    "EC014_unresolved_constant",
    controller_tags=_tag("MyConst", "DINT", is_const="true", no_data=True),
    routines=_rll_routine(rungs=_rung(0, "XIC(SomeTag)OTE(OutTag);")),
    prog_tags=_tag("SomeTag", "BOOL") + _tag("OutTag", "BOOL"),
)

# EC015: Tag with data type that has no definition
write(
    "EC015_invalid_data_type",
    controller_tags=_tag("MyTag", "NonExistentType"),
    routines=_rll_routine(rungs=_rung(0, "XIC(SomeTag)OTE(OutTag);")),
    prog_tags=_tag("SomeTag", "BOOL") + _tag("OutTag", "BOOL"),
)

# EC016: Array with zero dimension
write(
    "EC016_invalid_array_range",
    controller_tags=_tag("BadArr", "DINT", dims="0"),
    routines=_rll_routine(rungs=_rung(0, "XIC(SomeTag)OTE(OutTag);")),
    prog_tags=_tag("SomeTag", "BOOL") + _tag("OutTag", "BOOL"),
)

# EC017: Writing to a constant tag via OTE
write(
    "EC017_constant_modification",
    controller_tags=_tag("MyConst", "BOOL", is_const="true"),
    routines=_rll_routine(rungs=_rung(0, "OTE(MyConst);")),
)

# EC018: Program with empty routine (no body element)
write("EC018_empty_pou", routines=_empty_routine("Main", "RLL"))

# WC103: 16 branches on one rung
write(
    "WC103_cyclomatic_complexity",
    routines=_rll_routine(
        rungs=_rung(
            0,
            "XIC(A)OTE(Z);XIO(B)OTE(Z);XIC(C)OTE(Z);XIO(D)OTE(Z);XIC(E)OTE(Z);XIO(F)OTE(Z);XIC(G)OTE(Z);XIO(H)OTE(Z);XIC(I)OTE(Z);XIO(J)OTE(Z);XIC(K)OTE(Z);XIO(L)OTE(Z);XIC(M)OTE(Z);XIO(N)OTE(Z);XIC(O)OTE(Z);XIO(P)OTE(Z);",
        )
    ),
)

# WC106: AOI defined but never called
write(
    "WC106_unused_pou",
    aois=_aoi("MyUnusedAOI"),
    routines=_rll_routine(rungs=_rung(0, "XIC(SomeTag)OTE(OutTag);")),
    controller_tags=_tag("SomeTag", "BOOL") + _tag("OutTag", "BOOL"),
)

# WC107: Empty IF body (ST) — grammar now allows statement*
write(
    "WC107_empty_if_case",
    routines=_st_routine("Main", "IF x THEN END_IF"),
    controller_tags=_tag("x", "BOOL"),
)

# WC108: Deprecated instruction MSG used in RLL
write(
    "WC108_deprecated_instruction",
    routines=_rll_routine(rungs=_rung(0, "MSG(MyMsg);")),
    controller_tags=_tag("MyMsg", "MESSAGE"),
)

# WS101: REAL equality comparison
write(
    "WS101_float_equality",
    routines=_st_routine("Main", "flag := (r + 0.2) = 0.3;"),
    controller_tags=_tag("r", "REAL") + _tag("flag", "BOOL"),
)

# WS102: Division by literal zero
write(
    "WS102_div_by_zero",
    routines=_st_routine("Main", "result := x / 0;"),
    controller_tags=_tag("x", "DINT") + _tag("result", "DINT"),
)

# WS104: IF with DINT condition
write(
    "WS104_non_bool_condition",
    routines=_st_routine("Main", "IF myDINT THEN y:=1; END_IF"),
    controller_tags=_tag("y", "DINT"),
    prog_tags=_tag("myDINT", "DINT"),
)

# WS105: LINT to DINT implicit downcast
write(
    "WS105_implicit_downcast",
    routines=_st_routine("Main", "narrow := wide;"),
    controller_tags=_tag("narrow", "DINT") + _tag("wide", "LINT"),
)

# WS107: IF without ELSE
write(
    "WS107_missing_else",
    routines=_st_routine("Main", "IF x > 0 THEN y:=1; END_IF"),
    controller_tags=_tag("x", "DINT") + _tag("y", "DINT"),
)

# WS108: No-effect call ADD
write(
    "WS108_no_effect",
    routines=_st_routine("Main", "ADD(x, 1);"),
    controller_tags=_tag("x", "DINT"),
)

# WS109: Assignment to FOR loop variable
write(
    "WS109_for_var_assign",
    routines=_st_routine("Main", "FOR i:=1 TO 10 DO i:=i+1; END_FOR"),
)

# WS110: Dead code after RETURN
write(
    "WS110_dead_code",
    routines=_st_routine("Main", "RETURN; x := 1;"),
    controller_tags=_tag("x", "DINT"),
)

# WS111: Literal overflow — value exceeds DINT max
write(
    "WS111_literal_overflow",
    routines=_st_routine("Main", "big := 9999999999;"),
    controller_tags=_tag("big", "DINT"),
)

# WS112: Empty CASE branch
write(
    "WS112_empty_case_branch",
    routines=_st_routine("Main", "CASE x OF 1: 2: y:=1; END_CASE"),
    controller_tags=_tag("x", "DINT") + _tag("y", "DINT"),
)

# WS113: AND_THEN with non-BOOL left operand
write(
    "WS113_and_then_or_else",
    routines=_st_routine("Main", "IF myDINT OR_ELSE x > 0 THEN y:=1; END_IF"),
    controller_tags=_tag("myDINT", "DINT") + _tag("x", "DINT") + _tag("y", "DINT"),
)

# WS114: Mixed DINT + REAL in expression
write(
    "WS114_implicit_cast",
    routines=_st_routine("Main", "result := 1 + 2.5;"),
    controller_tags=_tag("result", "DINT"),
)

# ── RLL CHECKS ────────────────────────────────────────────────

write(
    "ER013_invalid_jmp_target", routines=_rll_routine(rungs=_rung(0, "JMP(BadLabel);"))
)
write("ER014_otl_without_otu", routines=_rll_routine(rungs=_rung(0, "OTL(MyBit);")))
write("ER015_mcr_zone", routines=_rll_routine(rungs=_rung(0, "MCR();")))
write("WR005_nop_present", routines=_rll_routine(rungs=_rung(0, "NOP();")))
write(
    "WR006_sus_production",
    routines=_rll_routine(rungs=_rung(0, "SUS(DebugTag);")),
    controller_tags=_tag("DebugTag", "STRING"),
)
write("WR007_inputs_no_output", routines=_rll_routine(rungs=_rung(0, "XIC(A)XIO(B);")))
write(
    "WR008_cop_overlap",
    routines=_rll_routine(rungs=_rung(0, "COP(MyArr[0],MyArr[1],10);")),
    controller_tags=_tag("MyArr", "DINT", dims="10"),
)
write(
    "WR009_gsv_invalid_class",
    routines=_rll_routine(rungs=_rung(0, "GSV(InvalidClass,Tag1,Tag2);")),
    controller_tags=_tag("Tag1", "DINT") + _tag("Tag2", "DINT"),
)
write("ER016_fal_incomplete", routines=_rll_routine(rungs=_rung(0, "FAL();")))

# ── ST CHECKS ────────────────────────────────────────────────

write(
    "ES001_invalid_expression_op",
    routines=_st_routine("Main", "result := MyString + 5;"),
    controller_tags=_tag("MyString", "STRING") + _tag("result", "DINT"),
)

write(
    "ES002_duplicate_case_value",
    routines=_st_routine("Main", "CASE x OF 1: a:=1; 1: b:=2; END_CASE"),
    controller_tags=_tag("x", "DINT") + _tag("a", "DINT") + _tag("b", "DINT"),
)

# ES003 needs body statement in FOR loop
write(
    "ES003_for_bounds",
    routines=_st_routine("Main", "FOR i:=0 TO 9999999999 DO x:=1; END_FOR"),
    controller_tags=_tag("x", "DINT"),
)

# ── LOGIX-SPECIFIC LIMITATIONS ─────────────────────────────────

# WS115: REPEAT loop (not supported by Logix)
write(
    "WS115_no_repeat",
    routines=_st_routine("Main", "REPEAT x:=x+1; UNTIL x>10 END_REPEAT"),
    controller_tags=_tag("x", "DINT"),
)

# WS116: GOTO not supported (check is always-pass since ST parser doesn't support GOTO)
# Create minimal test data — the check is a no-op placeholder
write(
    "WS116_no_goto",
    routines=_st_routine("Main", "x:=1;"),
    controller_tags=_tag("x", "DINT"),
)

# WS117: OR/XOR expression
write(
    "WS117_or_xor_limit",
    routines=_st_routine("Main", "result := a OR b;"),
    controller_tags=_tag("a", "DINT") + _tag("b", "DINT") + _tag("result", "DINT"),
)

# WS118: CASE with non-constant value
write(
    "WS118_case_constant",
    routines=_st_routine("Main", "CASE x OF myVar: y:=1; END_CASE"),
    controller_tags=_tag("x", "DINT") + _tag("myVar", "DINT") + _tag("y", "DINT"),
)
