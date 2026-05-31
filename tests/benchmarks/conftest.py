"""L5X file generators for benchmark tests.

Generates realistic L5X files with mixed RLL and ST content, various tag types,
arrays, and CDATA sections. Files are written to a temp directory and cleaned up
after the test session.
"""

import tempfile
import textwrap
from pathlib import Path

XML_HEADER = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<RSLogix5000Content SchemaRevision="1.0" SoftwareRevision="32.02" '
    'TargetType="Controller" ContainsContext="true">\n'
    '<Controller Name="Benchmark">\n'
)
XML_FOOTER = '</Controller>\n</RSLogix5000Content>\n'

TAG_TEMPLATES = {
    "DINT": '<Tag Name="{name}" TagType="Base" DataType="DINT" Radix="Decimal" '
            'Constant="false" ExternalAccess="Read/Write">'
            '<Data Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="0"/>'
            '</Data></Tag>\n',
    "BOOL": '<Tag Name="{name}" TagType="Base" DataType="BOOL" Radix="Decimal" '
            'Constant="false" ExternalAccess="Read/Write">'
            '<Data Format="Decorated"><DataValue DataType="BOOL" Radix="Decimal" Value="0"/>'
            '</Data></Tag>\n',
    "REAL": '<Tag Name="{name}" TagType="Base" DataType="REAL" Radix="Decimal" '
            'Constant="false" ExternalAccess="Read/Write">'
            '<Data Format="Decorated"><DataValue DataType="REAL" Radix="Decimal" Value="0.0"/>'
            '</Data></Tag>\n',
    "STRING": '<Tag Name="{name}" TagType="Base" DataType="STRING" Radix="Decimal" '
              'Constant="false" ExternalAccess="Read/Write">'
              '<Data Format="Decorated"><DataValue DataType="STRING" Radix="Decimal" Value=""/>'
              '</Data></Tag>\n',
    "DINT_ARRAY": '<Tag Name="{name}" TagType="Base" DataType="DINT" Radix="Decimal" '
                  'Constant="false" ExternalAccess="Read/Write" Dimensions="{dims}">'
                  '<Data Format="Decorated"><Array DataType="DINT" Dimensions="{dims}">'
                  '</Array></Data></Tag>\n',
}


def _tag(name: str, dtype: str = "DINT", dims: int = 0) -> str:
    if dims > 0:
        return TAG_TEMPLATES["DINT_ARRAY"].format(name=name, dims=dims)
    return TAG_TEMPLATES[dtype].format(name=name)


def _rung(num: int, text: str) -> str:
    return f'<Rung Number="{num}" Type="N"><Text><![CDATA[{text}]]></Text></Rung>\n'


def _rll_routine(name: str, rungs: str) -> str:
    return (
        f'<Routine Name="{name}" Type="RLL">\n<RLLContent>\n{rungs}</RLLContent>\n'
        f'</Routine>\n'
    )


def _st_routine(name: str, cdata: str) -> str:
    return (
        f'<Routine Name="{name}" Type="ST">\n<STContent>\n'
        f'<![CDATA[{cdata}]]>\n</STContent>\n</Routine>\n'
    )


def generate_rll_rungs(count: int, tag_pool_size: int) -> str:
    """Generate RLL rungs with realistic XIC/OTE patterns."""
    parts = []
    for i in range(count):
        t1 = f"Tag_{i % tag_pool_size}"
        t2 = f"Tag_{(i + 1) % tag_pool_size}"
        opcodes = [
            f"XIC({t1})OTE({t2});",
            f"XIO({t1})OTE({t2});",
            f"XIC({t1})XIC({t2})OTE(Bool_{i % max(tag_pool_size // 4, 1)});",
            f"LES({t1},{t2})OTE(Bool_{i % max(tag_pool_size // 4, 1)});",
            f"GRT({t1},{t2})OTE(Bool_{i % max(tag_pool_size // 4, 1)});",
        ]
        parts.append(_rung(i, opcodes[i % len(opcodes)]))
    return "".join(parts)


def generate_st_statements(count: int, tag_pool_size: int) -> str:
    """Generate ST statements with assignments, IFs, and binary ops."""
    parts = []
    for i in range(count):
        t = f"Tag_{i % tag_pool_size}"
        patterns = [
            f"{t} := {t} + 1;",
            f"{t} := {t} * 2;",
            f"IF {t} > 0 THEN {t} := {t} - 1; END_IF",
            f"{t} := {t} OR Tag_{(i + 1) % tag_pool_size};",
        ]
        parts.append(patterns[i % len(patterns)])
    return " ".join(parts)


def build_l5x(
    target_size_bytes: int,
    num_controller_tags: int = 200,
    num_bool_tags: int = 50,
    num_real_tags: int = 20,
    num_array_tags: int = 10,
    num_rll_routines: int = 2,
    num_st_routines: int = 1,
    rungs_per_routine: int = 500,
    st_stmts_per_routine: int = 200,
) -> str:
    """Build a valid L5X file targeting approximately target_size_bytes."""
    parts = [XML_HEADER]

    # DataTypes (empty — using built-in types only)
    parts.append('<DataTypes Use="Context"></DataTypes>\n')

    # Controller tags
    parts.append('<Tags Use="Context">\n')
    for i in range(num_controller_tags):
        parts.append(_tag(f"Tag_{i}", "DINT"))
    for i in range(num_bool_tags):
        parts.append(_tag(f"Bool_{i}", "BOOL"))
    for i in range(num_real_tags):
        parts.append(_tag(f"Real_{i}", "REAL"))
    for i in range(num_array_tags):
        parts.append(_tag(f"Arr_{i}", dims=100))
    parts.append('</Tags>\n')

    # Programs
    parts.append('<Programs Use="Context">\n')
    parts.append('<Program Name="MainProgram">\n<Tags Use="Context"></Tags>\n')
    parts.append('<Routines Use="Context">\n')

    # Main RLL routine
    all_rungs = ""
    for i in range(num_rll_routines):
        rungs = generate_rll_rungs(rungs_per_routine, num_controller_tags)
        all_rungs += _rll_routine(f"Main{i}" if i > 0 else "Main", rungs)
    parts.append(all_rungs)

    # ST routines
    for i in range(num_st_routines):
        stmts = generate_st_statements(st_stmts_per_routine, num_controller_tags)
        parts.append(_st_routine(f"ST_Main{i}", stmts))

    parts.append('</Routines>\n</Program>\n</Programs>\n')
    parts.append(XML_FOOTER)

    content = "".join(parts)

    # Pad or trim to approximate target size
    current_size = len(content.encode("utf-8"))
    if current_size < target_size_bytes:
        # Add more rungs to pad
        deficit = target_size_bytes - current_size
        # Each rung is roughly 80-120 bytes
        extra_rungs_needed = deficit // 100
        extra_rungs = generate_rll_rungs(extra_rungs_needed, num_controller_tags)
        # Insert before closing tags
        insert_point = content.rfind("</Routines>")
        content = content[:insert_point] + extra_rungs + content[insert_point:]

    return content


def write_l5x_to_temp(content: str) -> Path:
    """Write L5X content to a temp file and return the path."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="l5x_bench_"))
    path = tmp_dir / "benchmark.L5X"
    path.write_text(content, encoding="utf-8")
    return path


# Benchmark configurations: (label, target_bytes, description)
BENCHMARK_CONFIGS = [
    ("small", 100_000, "~100KB, 500 RLL rungs"),
    ("medium", 500_000, "~500KB, 2000 RLL rungs"),
    ("large", 2_000_000, "~2MB, 8000 RLL rungs"),
    ("xlarge", 10_000_000, "~10MB, 40000 RLL rungs"),
    ("xxlarge", 50_000_000, "~50MB, 200000 RLL rungs"),
]

# Expected baseline times in seconds (measured on developer machine)
# Tests assert time < baseline * multiplier
BASELINE_TIMES = {
    "small": 0.15,     # ~150ms observed
    "medium": 0.50,    # ~500ms observed
    "large": 2.50,     # ~2.5s observed
    "xlarge": 12.0,    # ~12s observed
    "xxlarge": 60.0,   # ~60s observed (extrapolated from linear trend)
}
