"""Generate benchmark L5X files with realistic mixed content.

Creates properly-indented L5X files with:
- Controller tags (DINT, BOOL, REAL, STRING, SINT, LINT, arrays, UDTs)
- User-defined data types (MotorParams, AlarmStruct, PIDparams)
- AddOn Instruction definitions with parameters, local tags, RLL routines
- Multiple programs with RLL and ST routines
- Task configuration
- RLL rungs with XIC/XIO/OTE/LES/GRT/EQU/MOV/ADD/TON/CTU/COP
- ST statements with assignments, IF/THEN, OR expressions

Run: python tests/data/benchmarks/generate.py
"""

from pathlib import Path
from xml.dom.minidom import Document

OUTPUT_DIR = Path(__file__).parent


class L5XWriter:
    """Builds an L5X XML document using minidom for proper indentation."""

    def __init__(self):
        self.doc = Document()

    def _elem(self, parent, tag, attrs=None):
        """Create and append an element, returning it."""
        el = self.doc.createElement(tag)
        if attrs:
            for k, v in attrs.items():
                el.setAttribute(k, str(v))
        parent.appendChild(el)
        return el

    def _text(self, parent, text):
        """Set text content on an element."""
        parent.appendChild(self.doc.createTextNode(text))

    def _cdata(self, parent, text):
        """Set CDATA content on an element."""
        parent.appendChild(self.doc.createCDATASection(text))

    def build(self):
        """Build the complete L5X document."""
        root = self._elem(
            self.doc,
            "RSLogix5000Content",
            {
                "SchemaRevision": "1.0",
                "SoftwareRevision": "32.02",
                "TargetType": "Controller",
                "ContainsContext": "true",
                "ExportDate": "Sat Mar 04 21:40:05 2023",
                "ExportOptions": "References NoRawData L5KData DecoratedData Context",
            },
        )
        ctrl = self._elem(root, "Controller", {"Name": "BenchmarkCtrl"})

        self._build_data_types(ctrl)
        self._build_controller_tags(ctrl)
        self._build_aois(ctrl)
        self._build_programs(ctrl)
        self._build_tasks(ctrl)
        self._build_modules(ctrl)

        return root

    def _build_data_types(self, parent):
        dts = self._elem(parent, "DataTypes", {"Use": "Context"})
        for name, family, members in [
            (
                "MotorParams",
                "NoFamily",
                [
                    ("Speed", "DINT"),
                    ("Torque", "REAL"),
                    ("Running", "BOOL"),
                    ("FaultCode", "SINT"),
                    ("Enabled", "BOOL"),
                ],
            ),
            (
                "AlarmStruct",
                "NoFamily",
                [
                    ("Active", "BOOL"),
                    ("Count", "DINT"),
                    ("Timestamp", "DINT"),
                ],
            ),
            (
                "PIDparams",
                "NoFamily",
                [
                    ("Setpoint", "REAL"),
                    ("Kp", "REAL"),
                    ("Ki", "REAL"),
                    ("Kd", "REAL"),
                    ("Output", "REAL"),
                    ("Error", "REAL"),
                ],
            ),
            (
                "ConveyorState",
                "NoFamily",
                [
                    ("Running", "BOOL"),
                    ("Speed", "DINT"),
                    ("JamCount", "DINT"),
                    ("Faulted", "BOOL"),
                    ("LastFault", "SINT"),
                ],
            ),
        ]:
            dt = self._elem(
                dts,
                "DataType",
                {
                    "Name": name,
                    "Family": family,
                    "Class": "User",
                },
            )
            members_el = self._elem(dt, "Members")
            for mname, mtype in members:
                self._elem(
                    members_el,
                    "Member",
                    {
                        "Name": mname,
                        "DataType": mtype,
                        "Dimension": "0",
                        "Radix": "Decimal",
                        "Hidden": "false",
                        "ExternalAccess": "Read/Write",
                    },
                )

    def _build_controller_tags(self, parent):
        tags = self._elem(parent, "Tags", {"Use": "Context"})

        # Basic typed tags
        for i in range(60):
            dtype = ["DINT", "BOOL", "REAL", "STRING", "SINT", "LINT"][i % 6]
            tag = self._elem(
                tags,
                "Tag",
                {
                    "Name": f"Ctrl{i}",
                    "TagType": "Base",
                    "DataType": dtype,
                    "Radix": "Decimal",
                    "Constant": "false",
                    "ExternalAccess": "Read/Write",
                },
            )
            data = self._elem(tag, "Data", {"Format": "Decorated"})
            self._elem(
                data,
                "DataValue",
                {
                    "DataType": dtype,
                    "Radix": "Decimal",
                    "Value": "0",
                },
            )

        # Array tags
        for i in range(6):
            tag = self._elem(
                tags,
                "Tag",
                {
                    "Name": f"Arr{i}",
                    "TagType": "Base",
                    "DataType": "DINT",
                    "Radix": "Decimal",
                    "Constant": "false",
                    "ExternalAccess": "Read/Write",
                    "Dimensions": "100",
                },
            )
            data = self._elem(tag, "Data", {"Format": "Decorated"})
            self._elem(
                data,
                "Array",
                {
                    "DataType": "DINT",
                    "Dimensions": "100",
                },
            )

        # UDT tags (MotorParams instances)
        for i in range(8):
            tag = self._elem(
                tags,
                "Tag",
                {
                    "Name": f"Motor{i}",
                    "TagType": "Base",
                    "DataType": "MotorParams",
                    "Radix": "NullType",
                    "Constant": "false",
                    "ExternalAccess": "Read/Write",
                },
            )
            data = self._elem(tag, "Data", {"Format": "Decorated"})
            struct = self._elem(data, "Structure", {"DataType": "MotorParams"})
            for mname, mtype, val in [
                ("Speed", "DINT", "0"),
                ("Torque", "REAL", "0.0"),
                ("Running", "BOOL", "0"),
                ("FaultCode", "SINT", "0"),
                ("Enabled", "BOOL", "0"),
            ]:
                self._elem(
                    struct,
                    "DataValueMember",
                    {
                        "Name": mname,
                        "DataType": mtype,
                        "Value": val,
                    },
                )

        # PID tags
        for i in range(4):
            tag = self._elem(
                tags,
                "Tag",
                {
                    "Name": f"PID{i}",
                    "TagType": "Base",
                    "DataType": "PIDparams",
                    "Radix": "NullType",
                    "Constant": "false",
                    "ExternalAccess": "Read/Write",
                },
            )
            data = self._elem(tag, "Data", {"Format": "Decorated"})
            struct = self._elem(data, "Structure", {"DataType": "PIDparams"})
            for mname in ["Setpoint", "Kp", "Ki", "Kd", "Output", "Error"]:
                self._elem(
                    struct,
                    "DataValueMember",
                    {
                        "Name": mname,
                        "DataType": "REAL",
                        "Value": "0.0",
                    },
                )

    def _build_aois(self, parent):
        aois = self._elem(parent, "AddOnInstructionDefinitions", {"Use": "Context"})

        for i in range(8):
            aoi = self._elem(
                aois,
                "AddOnInstructionDefinition",
                {
                    "Name": f"AOI_Motor{i}",
                    "Revision": "1.0",
                },
            )

            params = self._elem(aoi, "Parameters")
            self._elem(
                params,
                "Parameter",
                {
                    "Name": "EnableIn",
                    "TagType": "Base",
                    "DataType": "BOOL",
                    "Usage": "Input",
                    "Radix": "Decimal",
                    "Required": "false",
                    "Visible": "false",
                    "ExternalAccess": "Read Only",
                },
            )
            self._elem(
                params,
                "Parameter",
                {
                    "Name": "EnableOut",
                    "TagType": "Base",
                    "DataType": "BOOL",
                    "Usage": "Output",
                    "Radix": "Decimal",
                    "Required": "false",
                    "Visible": "false",
                    "ExternalAccess": "Read Only",
                },
            )
            self._elem(
                params,
                "Parameter",
                {
                    "Name": "SpeedRef",
                    "TagType": "Base",
                    "DataType": "DINT",
                    "Usage": "Input",
                    "Radix": "Decimal",
                    "Required": "true",
                    "Visible": "true",
                    "ExternalAccess": "Read/Write",
                },
            )
            self._elem(
                params,
                "Parameter",
                {
                    "Name": "Running",
                    "TagType": "Base",
                    "DataType": "BOOL",
                    "Usage": "Output",
                    "Radix": "Decimal",
                    "Required": "false",
                    "Visible": "true",
                    "ExternalAccess": "Read/Write",
                },
            )

            local_tags = self._elem(aoi, "LocalTags")
            self._elem(
                local_tags,
                "LocalTag",
                {
                    "Name": "SpeedActual",
                    "DataType": "DINT",
                    "Radix": "Decimal",
                    "ExternalAccess": "None",
                },
            )

            routines = self._elem(aoi, "Routines")
            routine = self._elem(
                routines,
                "Routine",
                {
                    "Name": "Logic",
                    "Type": "RLL",
                },
            )
            rll = self._elem(routine, "RLLContent")
            self._add_rung(rll, 0, "XIC(EnableIn)OTE(Running);")
            self._add_rung(rll, 1, "MOV(SpeedRef,SpeedActual);")

    def _build_programs(self, parent):
        programs = self._elem(parent, "Programs", {"Use": "Context"})

        for p in range(3):
            prog_name = "MainProgram" if p == 0 else f"Program{p}"
            prog = self._elem(programs, "Program", {"Name": prog_name})

            # Program-scoped tags
            prog_tags = self._elem(prog, "Tags", {"Use": "Context"})
            for i in range(15):
                dtype = ["DINT", "BOOL", "REAL"][i % 3]
                tag = self._elem(
                    prog_tags,
                    "Tag",
                    {
                        "Name": f"Prog{p}Tag{i}",
                        "TagType": "Base",
                        "DataType": dtype,
                        "Radix": "Decimal",
                        "Constant": "false",
                        "ExternalAccess": "Read/Write",
                    },
                )
                data = self._elem(tag, "Data", {"Format": "Decorated"})
                self._elem(
                    data,
                    "DataValue",
                    {
                        "DataType": dtype,
                        "Radix": "Decimal",
                        "Value": "0",
                    },
                )

            routines = self._elem(prog, "Routines", {"Use": "Context"})

            # Main RLL routine
            routine = self._elem(
                routines,
                "Routine",
                {
                    "Name": "Main",
                    "Type": "RLL",
                },
            )
            rll = self._elem(routine, "RLLContent")
            self._build_rll_rungs(rll, 200)

            # Secondary RLL routine
            routine2 = self._elem(
                routines,
                "Routine",
                {
                    "Name": "Control",
                    "Type": "RLL",
                },
            )
            rll2 = self._elem(routine2, "RLLContent")
            self._build_rll_rungs(rll2, 100)

            # ST routine
            routine3 = self._elem(
                routines,
                "Routine",
                {
                    "Name": "STLogic",
                    "Type": "ST",
                },
            )
            st = self._elem(routine3, "STContent")
            # Mix plain text and CDATA for ST statements
            stmts = self._build_st_statements(100)
            for text, use_cdata in stmts:
                if use_cdata:
                    self._cdata(st, text + "\n")
                else:
                    st.appendChild(self.doc.createTextNode(text + "\n"))

    def _build_rll_rungs(self, parent, count):
        opcodes = [
            lambda i: f"XIC(Ctrl{i % 30})OTE(Ctrl{(i + 1) % 30});",
            lambda i: f"XIO(Ctrl{i % 30})OTE(Ctrl{(i + 2) % 30});",
            lambda i: f"XIC(Ctrl{i % 30})XIC(Ctrl{(i + 1) % 30})OTE(Ctrl0);",
            lambda i: f"LES(Ctrl{i % 30},Ctrl{(i + 1) % 30})OTE(Ctrl0);",
            lambda i: f"GRT(Ctrl{i % 30},Ctrl{(i + 1) % 30})OTE(Ctrl1);",
            lambda i: (
                f"EQU(Ctrl{i % 30},Ctrl{(i + 1) % 30})MOV(Ctrl{i % 30},Arr0[{i % 10}]);"
            ),
            lambda i: (
                f"NEQ(Ctrl{i % 30},Ctrl{(i + 1) % 30})ADD(Ctrl{i % 30},Ctrl{(i + 1) % 30},Ctrl0);"
            ),
            lambda i: f"XIC(Ctrl{i % 30})TON(Timer{i % 10},5000,0);",
            lambda i: f"XIC(Ctrl{i % 30})CTU(Counter{i % 10},{(i + 1) % 30},100);",
            lambda i: f"COP(Arr{i % 6},Arr{(i + 1) % 6},10);",
        ]
        for i in range(count):
            text = opcodes[i % len(opcodes)](i)
            # ~80% plain text, ~20% CDATA (mostly for complex rungs)
            use_cdata = i % 5 == 0
            self._add_rung(parent, i, text, use_cdata)

    def _add_rung(self, parent, number, text, use_cdata=False):
        rung = self._elem(parent, "Rung", {"Number": str(number), "Type": "N"})
        td = self._elem(rung, "Text")
        if use_cdata:
            self._cdata(td, text)
        else:
            td.appendChild(self.doc.createTextNode(text))

    def _build_st_statements(self, count):
        """Return list of (text, use_cdata) tuples for ST statements."""
        stmts = []
        for i in range(count):
            t = f"Ctrl{i % 30}"
            # Simple assignments: plain text (no XML special chars)
            # IF/THEN: CDATA needed (contains > comparison)
            if i % 4 == 2:
                # IF statement - needs CDATA because of > in condition
                stmts.append((f"IF {t} > 0 THEN {t} := {t} - 1; END_IF", True))
            else:
                # Simple assignment - plain text is fine
                patterns = [
                    f"{t} := {t} + 1;",
                    f"{t} := {t} * 2;",
                    f"{t} := {t} OR Ctrl{(i + 1) % 30};",
                ]
                stmts.append((patterns[i % 3], False))
        return stmts

    def _build_tasks(self, parent):
        tasks = self._elem(parent, "Tasks", {"Use": "Context"})
        for name, sched, period, priority in [
            ("MainTask", "CONTINUOUS", 10, 0),
            ("Periodic1", "PERIODIC", 100, 1),
            ("Periodic2", "PERIODIC", 500, 2),
        ]:
            task = self._elem(
                tasks,
                "Task",
                {
                    "Name": name,
                    "Type": sched,
                    "Period": str(period),
                    "Priority": str(priority),
                    "WatchdogSize": "0",
                    "WatchdogValue": "0",
                    "InhibitUpdate": "false",
                },
            )
            progs = self._elem(task, "Programs")
            if name == "MainTask":
                self._elem(progs, "Program", {"Name": "MainProgram"})
            elif name == "Periodic1":
                self._elem(progs, "Program", {"Name": "Program1"})
            else:
                self._elem(progs, "Program", {"Name": "Program2"})

    def _build_modules(self, parent):
        modules = self._elem(parent, "Modules", {"Use": "Context"})
        for i in range(3):
            mod = self._elem(
                modules,
                "Module",
                {
                    "Name": f"Module{i}",
                    "Slot": str(i),
                    "ParentModPortId": "0",
                    "InhibitUpdate": "false",
                    "CatalogNumber": f"1756-IB32/{chr(65 + i)}",
                    "Vendor": "1",
                    "ProductType": "14",
                    "ProductCode": "16",
                    "Major": "2",
                    "Minor": "1",
                },
            )
            ports = self._elem(mod, "Ports")
            self._elem(
                ports,
                "Port",
                {
                    "Id": "0",
                    "Upstream": "true",
                },
            )

    def toxml(self):
        """Return the pretty-printed XML string."""
        return self.doc.toprettyxml(indent="  ")


def build_benchmark(target_bytes, label):
    """Build an L5X file targeting approximately target_bytes."""
    writer = L5XWriter()
    ctrl = writer.build()

    # Check current size
    xml = writer.toxml()
    current = len(xml.encode("utf-8"))

    if current < target_bytes:
        # Add more RLL rungs to pad
        programs_list = ctrl.getElementsByTagName("Programs")
        if programs_list:
            programs = programs_list[0]
            prog_list = programs.getElementsByTagName("Program")
            if prog_list:
                main_prog = prog_list[0]
                rll_list = main_prog.getElementsByTagName("RLLContent")
                if rll_list:
                    main_rll = rll_list[0]
                    deficit = target_bytes - current
                    extra_rungs = deficit // 150  # ~150 bytes per rung with indentation
                    writer._build_rll_rungs(main_rll, extra_rungs)
                    xml = writer.toxml()

    return xml


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
        xml = build_benchmark(target, label)
        path = OUTPUT_DIR / filename
        path.write_text(xml, encoding="utf-8")
        actual = path.stat().st_size
        print(f"  {label}: {actual / 1024:.0f} KB ({actual / (1024 * 1024):.1f} MB)")

    print("Done.")


if __name__ == "__main__":
    main()
