OPCODE_OPERANDS: dict[str, tuple[int | None, int | None]] = {
    # Bit
    "XIC": (1, 1), "XIO": (1, 1), "OTE": (1, 1), "OTL": (1, 1), "OTU": (1, 1),
    "ONS": (1, 1), "OSR": (1, 1), "OSF": (1, 1),
    # Timer/Counter
    "TON": (1, 1), "TOF": (1, 1), "RTO": (1, 1), "RES": (1, 1),
    "CTU": (1, 1), "CTD": (1, 1),
    # Math
    "ADD": (3, 3), "SUB": (3, 3), "MUL": (3, 3), "DIV": (3, 3),
    "MOD": (3, 3), "MOV": (2, 2), "CLR": (1, 1), "NEG": (1, 1),
    "CPT": (1, None), "SQR": (2, 2), "ABS": (1, 1),
    # Compare
    "EQU": (2, 2), "NEQ": (2, 2), "LES": (2, 2), "LEQ": (2, 2),
    "GRT": (2, 2), "GEQ": (2, 2), "GT": (2, 2), "CMP": (1, 1), "LIM": (3, 3),
    # Program control
    "JSR": (1, None), "JXR": (1, None), "JMP": (1, 1), "LBL": (1, 1),
    "MCR": (0, 0), "AFI": (0, 0), "NOP": (0, 0), "TND": (0, 0),
    "SUS": (1, 1),
    # Branching
    "BST": (0, 0), "BND": (0, 0), "NXB": (0, 0),
    # Conversion
    "SCL": (3, 3), "CPW": (2, 2), "SWPB": (2, 2),
    "DTOS": (2, 2), "STOD": (2, 2),
    # Process
    "PID": (1, 1),
    # Communication
    "MSG": (1, 1),
    # Misc
    "GSV": (3, 3), "SSV": (3, 3), "COP": (3, 3), "CPS": (3, 3),
    "FAL": (1, None), "FSC": (1, None), "IOT": (1, 1),
    "SFP": (1, 1), "SFR": (1, 1),
    "SPP": (3, None), "SRT": (2, 2),
}

INPUT_OPCODES: frozenset[str] = frozenset({
    "XIC", "XIO", "ONS", "OSR", "OSF",
    "EQU", "NEQ", "LES", "LEQ", "GRT", "GEQ", "GT", "CMP", "LIM",
})

OUTPUT_OPCODES: frozenset[str] = frozenset({
    "OTE", "OTL", "OTU",
    "TON", "TOF", "RTO", "CTU", "CTD",
    "MOV", "ADD", "SUB", "MUL", "DIV", "CLR", "NEG", "MOD",
    "SCL", "CPW", "SWPB", "DTOS", "STOD",
    "PID", "MSG", "IOT",
    "COP", "CPS",
    "FAL", "FSC",
    "GSV", "SSV",
})

INSTRUCTION_TYPES: dict[str, dict[int, str]] = {
    "TON": {0: "TIMER"},
    "TOF": {0: "TIMER"},
    "RTO": {0: "TIMER"},
    "CTU": {0: "COUNTER"},
    "CTD": {0: "COUNTER"},
    "RES": {0: "TIMER"},
    "PID": {0: "PID"},
    "MSG": {0: "MESSAGE"},
    "IOT": {0: "DINT"},
}
