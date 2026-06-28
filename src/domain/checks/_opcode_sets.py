"""Centralized opcode definitions for RLL/ST check logic.

All opcode frozensets used by check functions live here. Checks import
from this module instead of defining their own duplicates.

Opcode naming:
  - Classic names: valid in all L5X versions (v32+)
  - v36+ aliases:  introduced in Rockwell v36, map to classic names

Version-aware helpers:
  - builtin_opcodes(revision) -> frozenset valid for the given version
  - resolve_opcode(name, revision) -> canonical classic name
"""

# ---------------------------------------------------------------------------
# Classic opcodes (valid in all L5X versions v32+)
# ---------------------------------------------------------------------------

MATH_OPS: frozenset[str] = frozenset(
    {"ADD", "SUB", "MUL", "DIV", "MOD", "CLR", "NEG", "CPT", "SQR", "ABS"}
)

COMPARE_OPS: frozenset[str] = frozenset(
    {"EQU", "NEQ", "LES", "LEQ", "GRT", "GEQ", "GT", "CMP", "LIM"}
)

BIT_OPS: frozenset[str] = frozenset({"XIC", "XIO", "OTE", "OTL", "OTU"})

TIMER_COUNTER_OPS: frozenset[str] = frozenset(
    {"TON", "TOF", "RTO", "CTU", "CTD", "RES"}
)

INPUT_OPCODES: frozenset[str] = (
    frozenset({"XIC", "XIO", "ONS", "OSR", "OSF"}) | COMPARE_OPS
)

OUTPUT_OPCODES: frozenset[str] = frozenset(
    {
        "OTE",
        "OTL",
        "OTU",
        "TON",
        "TOF",
        "RTO",
        "CTU",
        "CTD",
        "RES",
        "MOV",
        "ADD",
        "SUB",
        "MUL",
        "DIV",
        "CLR",
        "NEG",
        "MOD",
        "SCL",
        "CPW",
        "SWPB",
        "DTOS",
        "STOD",
        "PID",
        "MSG",
        "IOT",
        "COP",
        "CPS",
        "FAL",
        "FSC",
        "GSV",
        "SSV",
    }
)

# ST calls that are pure functions (no side effects, return a value)
ST_PURE_CALLS: frozenset[str] = frozenset(
    {
        "ADD",
        "SUB",
        "MUL",
        "DIV",
        "MOD",
        "NEG",
        "ABS",
        "SQR",
        "GT",
        "LT",
        "GEQ",
        "LEQ",
        "EQU",
        "NEQ",
        "AND",
        "OR",
        "NOT",
        "XOR",
    }
)

# Deprecated instructions still in OPCODE_OPERANDS (so EC003 does not fire)
DEPRECATED_OPCODES: frozenset[str] = frozenset({"MSG", "PID", "DDT"})

# ---------------------------------------------------------------------------
# v36+ aliases — new names Rockwell introduced in v36
# Each maps an alias to its classic counterpart.
# ---------------------------------------------------------------------------

_V36_ALIAS_TO_CLASSIC: dict[str, str] = {
    "EQ": "EQU",
    "NE": "NEQ",
    "LT": "LES",
    "LE": "LEQ",
    "GE": "GEQ",
    "MOVE": "MOV",
}

V36_ALIASES: frozenset[str] = frozenset(_V36_ALIAS_TO_CLASSIC)

# The classic names that have v36+ aliases
_CLASSICS_WITH_ALIASES: frozenset[str] = frozenset(_V36_ALIAS_TO_CLASSIC.values())


def _parse_major(revision: str) -> int:
    """Extract major version int from a 'Major.Minor' string."""
    try:
        return int(revision.split(".")[0])
    except (ValueError, IndexError):
        return 0


def builtin_opcodes(revision: str = "") -> frozenset[str]:
    """Return the set of builtin opcode names valid for the given version.

    For v36+, both classic names and new aliases are included.
    For pre-v36, only classic names are included.
    """
    base: frozenset[str] = (
        MATH_OPS
        | COMPARE_OPS
        | BIT_OPS
        | TIMER_COUNTER_OPS
        | frozenset(
            {
                "JSR",
                "JXR",
                "JMP",
                "LBL",
                "MCR",
                "AFI",
                "NOP",
                "TND",
                "SUS",
                "BST",
                "BND",
                "NXB",
                "ONS",
                "OSR",
                "OSF",
                "SCL",
                "CPW",
                "SWPB",
                "DTOS",
                "STOD",
                "PID",
                "MSG",
                "GSV",
                "SSV",
                "COP",
                "CPS",
                "FAL",
                "FSC",
                "IOT",
                "SFP",
                "SFR",
                "SPP",
                "SRT",
                "MOV",
            }
        )
    )
    major = _parse_major(revision)
    if major >= 36:
        return base | V36_ALIASES
    return base


def resolve_opcode(name: str, revision: str = "") -> str:
    """Map a v36+ alias to its classic name if applicable.

    Returns the classic name regardless of version (for consistent lookup
    in OPCODE_OPERANDS, classification sets, etc.).
    """
    upper = name.upper()
    if upper in _V36_ALIAS_TO_CLASSIC:
        return _V36_ALIAS_TO_CLASSIC[upper]
    return upper
