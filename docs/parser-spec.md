# L5X Parser Specification

Defines how L5X XML and RLL neutral text are parsed into an AST that `l5x-lint` consumes.

---

## 1. L5X XML Parsing

### 1.1 Entry Point

Parse an L5X file (`.L5X` XML) into the typed object model defined below.

```python
def parse_l5x(file_or_string: str | Path) -> L5XProject:
    ...
```

### 1.2 Object Model

```
L5XProject
  ├── schema_revision: str           # "1.0"
  ├── software_revision: str         # "20.01" — determines XSD version
  ├── target_name: str
  ├── target_type: str               # "Routine", "Program", "Controller"
  ├── controller: Controller
  └── export_options: list[str]

Controller
  ├── name: str
  ├── processor_type: str | None
  ├── major_revision: int
  ├── minor_revision: int
  ├── data_types: list[DataType]
  ├── tags: list[Tag]
  ├── programs: list[Program]
  ├── tasks: list[Task]
  ├── add_on_instructions: list[AOI]
  └── modules: list[Module]

DataType
  ├── name: str                      # "MyUDT", "TIMER" (built-in reference)
  ├── family: str                    # "NoFamily", "StringFamily"
  ├── class: str                     # "User", "IO", "ProductDefined"
  ├── members: list[Member]
  └── description: str | None

Member
  ├── name: str
  ├── data_type: str                 # "DINT", "BOOL", nested UDT name
  ├── dimension: int                 # 0 = scalar, N = array of N
  ├── radix: str                     # "Decimal", "Float", "Binary", etc.
  ├── hidden: bool                   # BIT backing fields, internal members
  ├── target: str | None             # BIT members: backing field name
  ├── bit_number: int | None         # BIT members: bit offset
  └── external_access: str           # "Read/Write", "Read Only", "None"

Tag
  ├── name: str
  ├── tag_type: str                  # "Base", "Alias", "Consumed", "Produced"
  ├── data_type: str                 # "BOOL", "DINT", "TIMER", "MyUDT", "STRING[100]"
  ├── dimensions: list[int]          # [] scalar, [10] 1-D, [3,4] 2-D
  ├── radix: str | None              # None for struct types
  ├── constant: bool
  ├── external_access: str
  ├── alias_for: str | None          # Only if tag_type == "Alias"
  └── description: str | None

Program
  ├── name: str
  ├── tags: list[Tag]
  ├── routines: list[Routine]
  ├── main_routine_name: str | None
  └── fault_routine_name: str | None

Routine
  ├── name: str
  ├── type: Literal["RLL", "ST", "FBD", "SFC"]
  └── rungs: list[ParsedRung]        # RLL; ST has statements, FBD has wire graph

Task
  ├── name: str
  ├── type: str                      # "PERIODIC", "CONTINUOUS", "EVENT"
  ├── rate: int | None               # ms; None for CONTINUOUS
  ├── priority: int
  ├── watchdog: int                  # ms
  ├── inhibit_task: bool
  └── scheduled_programs: list[str]  # program names

AOI
  ├── name: str
  ├── revision: str                  # "1.000"
  ├── parameters: list[AOIParameter]
  ├── local_tags: list[Tag]
  ├── routines: list[Routine]
  ├── execute_prescan: bool
  ├── execute_postscan: bool
  └── execute_enable_in_false: bool

AOIParameter
  ├── name: str
  ├── data_type: str
  ├── usage: str                     # "Input", "Output", "InOut"
  ├── dimensions: list[int]
  ├── required: bool
  ├── visible: bool
  └── external_access: str

Module
  ├── name: str
  ├── catalog_number: str
  ├── vendor: int
  ├── product_type: int
  ├── product_code: int
  ├── revision: (major: int, minor: int)
  ├── parent_module: str
  ├── inhibited: bool
  └── ports: list[Port]
```

### 1.3 Parsing Rules

**Rule 1 — Controller-scope vs Program-scope tags:**
`<Tags>` children of `<Controller>` → `controller.tags`
`<Tags>` children of `<Program>` → `program.tags`

**Rule 2 — Data value extraction:**
Prefer `Data[@Format='Decorated']` for value access.
Fall back to `Data[@Format='L5K']` for primitive scalars.
Ignore raw hex `Data` elements (no Format attribute).

**Rule 3 — Data type resolution:**
Known built-in types (BOOL, SINT, INT, DINT, LINT, USINT, UINT, UDINT, ULINT, REAL, LREAL, TIMER, COUNTER, CONTROL, STRING, MESSAGE) are resolved from an internal table — see Rule 5.
User-defined types are resolved from `Controller.DataTypes`.

**Rule 4 — Array dimensions:**
`Dimensions` attribute on `Tag` or `Member` — comma- or space-separated integers.
`[]` for scalar, `[N]` for 1-D, `[N,M]` for 2-D, `[N,M,P]` for 3-D.

**Rule 5 — Built-in struct members (from reference data):**

| Type | Members |
|------|---------|
| TIMER | PRE(DINT), ACC(DINT), EN(BOOL), TT(BOOL), DN(BOOL) |
| COUNTER | PRE(DINT), ACC(DINT), CU(BOOL), CD(BOOL), DN(BOOL), OV(BOOL), UN(BOOL) |
| CONTROL | LEN(DINT), POS(DINT), EN(BOOL), EU(BOOL), DN(BOOL), EM(BOOL), ER(BOOL), UL(BOOL), IN(BOOL), FD(BOOL) |
| STRING | LEN(DINT), DATA(STRING) |

These are implicit — they never appear in `<DataTypes>`.

**Rule 6 — Alias resolution:**
If `TagType="Alias"`, set `tag.alias_for` from the `AliasFor` attribute.
The linter resolves the alias to the target tag's data type.

**Rule 7 — AOI parameter mapping:**
AOI `<Parameter>` elements become `AOIParameter` objects.
`Usage` maps to "Input", "Output", or "InOut" for type checking.
AOI `<LocalTag>` elements become program-scoped `Tag` objects.

---

## 2. RLL Neutral Text Grammar

### 2.1 Lexical Tokens

```
OPCODE    : [A-Z_][A-Z0-9_]*       # XIC, OTE, TON, MOV, ...
TAG_NAME  : [A-Za-z_][A-Za-z0-9_]*
           (\. [A-Za-z_][A-Za-z0-9_]*)*    # Tag.Member.SubMember
           (\[ INT \])*                    # Tag[0], Tag[1][2]
NUMBER    : -? [0-9]+ (\.[0-9]+)?  # 42, 3.14, -5
COMMA     : ,
LPAREN    : \(
RPAREN    : \)
LBRACKET  : \[
RBRACKET  : \]
SEMICOLON : ;
```

### 2.2 Grammar (LALR(1))

```
rung           : input_list output_list SEMICOLON
               | output_list SEMICOLON

input_list     : input_instruction
               | input_list input_instruction
               | input_branch
               | input_list input_branch

input_branch   : LBRACKET input_level RBRACKET

input_level    : input_list
               | input_list COMMA input_level
               | COMMA
               | COMMA input_level

output_list    : output_seq
               | output_branch

output_seq     : output_instruction
               | output_seq output_instruction

output_branch  : LBRACKET output_level RBRACKET

output_level   : input_list output_list
               | output_list
               | input_list output_list COMMA output_level
               | output_list COMMA output_level

input_instruction : OPCODE LPAREN params RPAREN

output_instruction : OPCODE LPAREN params RPAREN

params         : param
               | params COMMA param

param          : TAG_NAME
               | NUMBER
               | QUESTION_MARK     # "?" — unused/unassigned operand
```

### 2.3 Parsed Rung AST

```python
@dataclass
class ParsedRung:
    number: int
    text: str                       # raw neutral text
    inputs: list[Instruction | Branch]
    outputs: list[Instruction | Branch]

@dataclass
class Instruction:
    opcode: str                     # "XIC", "OTE", "TON", ...
    operands: list[Operand]
    position: RungPosition          # which branch/level

@dataclass
class Branch:
    inputs: list[Instruction | Branch]   # parallel branches
    outputs: list[Instruction | Branch]

@dataclass
class Operand:
    type: Literal["tag", "number", "wildcard"]
    value: str                      # "Motor_Run", "42", "?"
    tag_parts: list[str] | None     # ["Motor_Run"] or ["Timer1", "PRE"]
    array_indices: list[int] | None # None if scalar, [0] if array element
```

### 2.4 Branch Semantics

```
XIC(A)[XIO(B),XIO(C)]OTE(D);
```
Parses as:
- input_instruction: XIC(A)
- input_branch: parallel (OR) of XIO(B) and XIO(C)
- output_instruction: OTE(D)

The linter needs to understand branches for:
- Checking operand types inside parallel branches
- Tracking which tags are referenced in each branch path

---

## 3. Instruction Operand Rules (For Type Checking)

### 3.1 Category by Operand Count

| Count | Opcodes |
|-------|---------|
| 0 | AFI, NOP, END, MCR |
| 1 | XIC, XIO, ONS, OSR, OTE, OTU, OTL, RES, CLR, UID, UIE, REF, FFU, FFL, LBL, JMP, RET, TND, SUS |
| 2 | EQU, NEQ, GRT, GEQ, LES, LEQ, MEQ, MOV, MVM, SWPB, FRD, TOD, TRUNC, ABS, NEG, NOT, ENUM, DEC, INP, ITV |
| 3 | ADD, SUB, MUL, DIV, MOD, AND, OR, XOR, TON, TOF, RTO, CTU, CTD, COP, CPS, SIZE, FAL, LBL (JSR format), JSR |
| 4 | LIM, SCL, PID, DDT, BFL, BFLD |
| 5 | BTD, BTDT |
| variable | CPT, GSV, SSV, SRT, FBC, DDT, ASN, ACOS, ATN, COS, LN, LOG, SIN, TAN, SQP, SQC |

### 3.2 Operand Type Constraints

**Each opcode defines the expected type for each operand position:**
```
XIC  : [0: BOOL]          — tag must be BOOL or SINT/INT/DINT bit access
XIO  : [0: BOOL]
OTE  : [0: BOOL]
OTL  : [0: BOOL]
OTU  : [0: BOOL]
TON  : [0: TIMER]        — first operand must be TIMER or TIMER[]
TOF  : [0: TIMER]
RTO  : [0: TIMER]
CTU  : [0: COUNTER]
CTD  : [0: COUNTER]
RES  : [0: TIMER | COUNTER]
MOV  : [0: any, 1: same_as_0]   — source/dest must match
ADD  : [0: numeric, 1: numeric, 2: numeric]
SUB  : [0: numeric, 1: numeric, 2: numeric]
MUL  : [0: numeric, 1: numeric, 2: numeric]
DIV  : [0: numeric, 1: numeric, 2: numeric]
EQU  : [0: any, 1: same_as_0]
GRT  : [0: numeric, 1: numeric]
LES  : [0: numeric, 1: numeric]
JSR  : [0: routine_name]  — must match a routine in the same program
```

**Wildcard operands:**
TON/TON/TOF/RTO/CTU/CTD use `?` for PRE and ACC positions in the neutral text
(e.g., `TON(Timer1,?,?)`). These are placeholders; the linter ignores them but
must still validate the correct operand count.

### 3.3 Type Compatibility Matrix

| Source Tag Type | Compatible Dest Types |
|-----------------|----------------------|
| BOOL | BOOL, SINT, INT, DINT (bit 0) |
| SINT | SINT, INT, DINT, LINT, REAL |
| INT | INT, DINT, LINT, REAL |
| DINT | DINT, LINT, REAL |
| LINT | LINT, REAL |
| REAL | REAL |
| TIMER | TIMER |
| COUNTER | COUNTER |
| UDT | same UDT only |

---

## 4. Built-in Type Resolution

### 4.1 Internal Type Registry

```python
BUILTIN_TYPES: dict[str, DataType] = {
    "BOOL":    DataType("BOOL", "NoFamily", "ProductDefined", []),
    "SINT":    DataType("SINT", "NoFamily", "ProductDefined", []),
    "INT":     DataType("INT", "NoFamily", "ProductDefined", []),
    "DINT":    DataType("DINT", "NoFamily", "ProductDefined", []),
    "LINT":    DataType("LINT", "NoFamily", "ProductDefined", []),
    "USINT":   DataType("USINT", "NoFamily", "ProductDefined", []),
    "UINT":    DataType("UINT", "NoFamily", "ProductDefined", []),
    "UDINT":   DataType("UDINT", "NoFamily", "ProductDefined", []),
    "ULINT":   DataType("ULINT", "NoFamily", "ProductDefined", []),
    "REAL":    DataType("REAL", "NoFamily", "ProductDefined", []),
    "LREAL":   DataType("LREAL", "NoFamily", "ProductDefined", []),
    "TIMER":   DataType("TIMER", "NoFamily", "ProductDefined", [
        Member("PRE", "DINT", 0, "Decimal", False, None, None, "Read/Write"),
        Member("ACC", "DINT", 0, "Decimal", False, None, None, "Read/Write"),
        Member("EN", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("TT", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("DN", "BOOL", 0, None, False, None, None, "Read/Write"),
    ]),
    "COUNTER": DataType("COUNTER", "NoFamily", "ProductDefined", [
        Member("PRE", "DINT", 0, "Decimal", False, None, None, "Read/Write"),
        Member("ACC", "DINT", 0, "Decimal", False, None, None, "Read/Write"),
        Member("CU", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("CD", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("DN", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("OV", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("UN", "BOOL", 0, None, False, None, None, "Read/Write"),
    ]),
    "CONTROL":  DataType("CONTROL", "NoFamily", "ProductDefined", [
        Member("LEN", "DINT", 0, "Decimal", False, None, None, "Read/Write"),
        Member("POS", "DINT", 0, "Decimal", False, None, None, "Read/Write"),
        Member("EN", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("EU", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("DN", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("EM", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("ER", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("UL", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("IN", "BOOL", 0, None, False, None, None, "Read/Write"),
        Member("FD", "BOOL", 0, None, False, None, None, "Read/Write"),
    ]),
    "STRING":   DataType("STRING", "StringFamily", "ProductDefined", [
        Member("LEN", "DINT", 0, "Decimal", False, None, None, "Read/Write"),
        Member("DATA", "STRING", 0, "ASCII", False, None, None, "Read/Write"),
    ]),
    "MESSAGE":  DataType("MESSAGE", "NoFamily", "ProductDefined", []),
}
```

### 4.2 Member Access Resolution

When a tag is referenced with member access (e.g., `Timer1.PRE`):
1. Resolve the tag's base data type → TIMER
2. Look up `.PRE` in TIMER's members → Member("PRE", "DINT", ...)
3. Resulting type is DINT

For nested access (`MyUDT.Inner.Value`):
1. Resolve MyUDT → find DataType "MyUDT" from `controller.data_types`
2. Find member "Inner" → get its data type
3. Resolve that type → find DataType or built-in
4. Find member "Value" → final type

### 4.3 Array Index Resolution

When a tag has array dimensions (e.g., `MyArray[5]` where `Dimensions="10"`):
1. Check that index `5` is within bounds `[0, 10)`
2. The element type is the tag's base data type (strip brackets)

For multi-dimensional (`MyMatrix[2,3]` where `Dimensions="4,5"`):
1. Check each dimension: `2 < 4`, `3 < 5`
2. Element type is the base data type

---

## 5. XSD Schema Validation (from l5x-schema)

The `l5x-schema` repo provides XSD files for:
- Schema revision 1.0 (firmware 20.x)
- Schema revision 1.1 (firmware 31.x+)

Validation approach:
1. Read `SchemaRevision` attribute from `<RSLogix5000Content>`
2. Load corresponding XSD from `references/l5x-schema/`
3. Validate structural XML against XSD
4. Report structural errors (missing required attributes, wrong element order, etc.)

---

## 6. Error & Warning Codes (From l5x-lint spec)

```
ERRORS:
  E001  Undefined tag reference
  E002  Type mismatch
  E003  Missing AOI definition
  E004  Invalid JSR target
  E005  Invalid UDT member access
  E006  Array index out of bounds
  E007  Duplicate tag name in scope
  E008  AOI circular dependency
  E009  Wrong operand count
  E010  Cross-scope tag violation

WARNINGS:
  W001  Unused tag declared
  W002  Unreachable rung
  W003  Output never driven
  W004  Timer PRE never set
  W005  Shadowed tag name
```

---

## 7. Implementation Notes

### 7.1 Decision: Leverage Existing Libraries vs Rebuild

**XML Parsing — USE EXISTING (`jvalenzuela/l5x`):**
The `l5x` Python library is a mature, tested L5X reader/writer that handles:
- Full project/controller/program/tag/routine object model
- Decorated data, L5K data, arrays, structures, aliases, message tags
- Bit-level access, UDT member resolution
- CDATA sections (the tricky part of L5X XML)

Building a custom XML parser would duplicate hundreds of lines of tested code
for zero benefit. The linter only needs to **adapt** `l5x`'s output into its
`SymbolTable` — not replace it entirely.

**RLL Neutral Text — PARTIAL REBUILD using Lark:**
`alairjunior/l5x2c` has a working PLY-based RLL parser covering ~25 instructions.
But it misses ~75 instructions (math, comparison, PID, GSV/SSV, FAL, DDT, etc.)
and PLY grammars are harder to maintain than Lark.

Strategy: Use `lark` with the grammar from §2.2, using `l5x2c`'s parser as
reference for branch syntax and instruction patterns. This gives us:
- Complete instruction coverage (add new opcodes declaratively in the grammar)
- Better error messages (critical for linter diagnostics)
- Readable, maintainable grammar file

### 7.2 Recommended Parser Approach

**Layer 1 — XML adapter:**
- Use `l5x` library (`from l5x import Project`) to parse L5X XML
- Map `Project.controller.tags` and `program.tags` to linter's `SymbolTable`
- Map `DataType` definitions to internal type registry
- Wrap the library, don't reimplement it

**Layer 2 — RLL neutral text parser:**
- Use `lark` (LALR parser) with the grammar from §2.2
- Build the `ParsedRung` AST from §2.3
- Handle branch structures for parallel logic

**Layer 3 — Symbol table builder:**
- Build symbol tables from parsed tags + data types
- Resolve UDT members and built-in types
- Track scope hierarchy (controller → program → routine)

### 7.3 Key Dependencies

```
l5x           — L5X XML parsing (jvalenzuela/l5x or fork)
lark          — RLL neutral text parsing (LALR parser generator)
pydantic      — Optional: typed object models for linter output
xmlschema     — Optional: XSD validation via l5x-schema
pytest        — Test framework
```

### 7.4 Module Structure

```
l5x_lint/
  __init__.py
  adapter.py          # l5x library → linter's SymbolTable (Layer 1)
  rll_grammar.py      # Lark grammar definition (Layer 2)
  rll_parser.py       # Lark transformer → ParsedRung AST (Layer 2)
  builtins.py         # Built-in type registry (§4.1)
  symbol_table.py     # Scope-aware tag/type resolution
  type_checker.py     # Type compatibility checks
  analyzer.py         # SemanticAnalyzer orchestrating checks
  checks.py           # Individual check implementations (E001-E010, W001-W005)
  diagnostics.py      # Diagnostic output model
  mcp_server.py       # FastMCP tool server

tests/
  conftest.py
  test_data_inventory.py
  data/
    valid/            # 14+ working L5X files for baseline
    invalid/          # 14 intentionally broken files, one per error code
```
