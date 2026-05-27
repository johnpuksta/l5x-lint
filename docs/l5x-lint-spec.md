# l5x-lint — Semantic Analyzer for L5X PLC Programs

**Phase 2 of the L5X Autonomous PLC Agent Toolchain**

---

## Purpose

Semantic analyzer — the "dotnet build" / compiler equivalent.
Consumes an L5X AST and produces structured, agent-readable diagnostics.
No execution — pure static analysis.

---

## Architecture: Functional Pipeline + Ports & Adapters

**Principles:**
- **Functional core, imperative shell** — all business logic is pure functions returning `Result` or `list[Diagnostic]`. IO (file reading, MCP server) lives at the edges.
- **Railway Oriented Programming** — each step returns `Result[T, LintError]`. Composition via `flow` + `bind`, not try/except.
- **No None** — `Maybe[Tag]` instead of `Tag | None`. Forces explicit handling.
- **Typed errors** — `LintError` is a union of dataclass variants, not a string.
- **One function per check** — each E/W code is a standalone pure function, easy to test in isolation.

### Data Flow

```
                      ┌──────────────────────────┐
XML string ─────────►│  adapter.py               │
                      │  ElementTree (primary)    │
                      │  l5x lib (tag value opt.) │
                      │  → Result[L5XProject]     │
                      └──────────┬───────────────┘
                                 ▼
                      ┌──────────────────────────┐
                      │  SymbolTable(project)    │
                      │  (pure construction)     │
                      └──────────┬───────────────┘
                                 ▼
              ┌──────────────────┴──────────────────┐
              ▼                                     ▼
  ┌──────────────────────┐              ┌──────────────────────┐
  │  rung_parser.py      │              │  st_parser.py        │
  │  Lark LALR           │              │  Lark LALR           │
  │  → ParsedRung[]      │              │  → StProgram         │
  └──────────┬───────────┘              └──────────┬───────────┘
              │                                     │
              └──────────┬──────────────────────────┘
                                 ▼
                ┌─────────────────────────────────────┐
                │  checks/*.py                         │
                │  Each: (SymbolTable, content)        │
                │       → list[Diagnostic]             │
                │  Composed via flow:                  │
                │  flow(project,                       │
                │    build_symbol_tables,              │
                │    bind(parse_all_routine_content),   │
                │    bind(run_all_checks))              │
                └──────────┬──────────────────────────┘
                          ▼
               ┌──────────────────────┐
               │  AnalysisResult      │
               │  { passed, errors,   │
               │    warnings, fixes } │
               └──────────────────────┘
```

### Functional Patterns

```python
from returns.result import Result, Success, Failure, safe
from returns.maybe import Maybe, Some, Nothing
from returns.pipeline import flow
from returns.pointfree import bind

# Result for fallible operations
def resolve_tag(name: str, scope: SymbolTable) -> Result[Tag, LintError]:
    match scope.lookup(name):
        case Nothing: return Failure(LintError.E001(name))
        case Some(tag): return Success(tag)

# flow for linear pipelines (no try/except)
result = flow(input, step1, bind(step2), bind(step3))

# @safe converts exceptions → Failure automatically
@safe
def parse_l5x(xml: str) -> L5XProject: ...

# Maybe instead of None
def lookup(self, name: str) -> Maybe[Tag]: ...

# Checks return list[Diagnostic] — they always "succeed", may produce 0 results
def check_undefined_tags(routine: Routine, scope: SymbolTable) -> list[Diagnostic]:
    return [
        Diagnostic("E001", f"Undefined tag '{ref}'", loc)
        for ref in extract_tag_refs(routine)
        if scope.lookup(ref) is Nothing
    ]
```

---

## Core Type Definitions

All domain types are pure dataclasses — zero dependencies, no pydantic.
These are the single source of truth; every module imports from `domain/`.

### TagPath

```python
@dataclass
class TagPath:
    """A dotted tag path with optional array indices, e.g. `Conveyor.Motor[3].Speed`."""
    segments: list[TagPathSegment]

    @property
    def full_name(self) -> str:
        return ".".join(s.path_str() for s in self.segments)

    def resolve(self, scope: SymbolTable) -> Result[Tag, LintError]:
        ...

@dataclass
class TagPathSegment:
    name: str
    index: int | None = None          # Arr[5] → name="Arr", index=5

    def path_str(self) -> str:
        return f"{self.name}[{self.index}]" if self.index is not None else self.name
```

### Location

```python
@dataclass
class Location:
    program: str
    routine: str
    rung: int | None = None           # RLL rung number
    line: int | None = None           # ST line number
```

### Diagnostic

```python
@dataclass
class Diagnostic:
    code: str                         # "E001", "W003", etc.
    severity: str                     # "error" | "warning"
    location: Location
    message: str
    hint: str | None = None
    fix_suggestion: str | None = None
```

### AnalysisResult

```python
@dataclass
class AnalysisResult:
    passed: bool
    error_count: int
    warning_count: int
    diagnostics: list[Diagnostic]
```

### FixSuggestion

```python
@dataclass
class FixSuggestion:
    code: str
    description: str
    replacement: str | None = None    # CDATA text replacement for the rung/line
    target_tag: str | None = None     # tag to create/rename
```

### LintError (typed union for Result error type) — ✅ IMPLEMENTED

All 15 variants — one per E/W code. Used as the `Error` type in `Result[_, LintError]`.
Each variant is self-describing: `.code`, `.severity`, `.message`, `.description`.

```python
from typing import ClassVar
import dataclasses as _dc

class LintErrorBase:
    code: ClassVar[str]
    severity: ClassVar[str]
    description: ClassVar[str]
    message_template: ClassVar[str]

    @property
    def message(self) -> str:
        fields = {f.name: getattr(self, f.name) for f in _dc.fields(self)}
        return self.message_template.format(**fields)

@dataclass
class E001(LintErrorBase):
    code: ClassVar[str] = "E001"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Undefined tag reference '{name}'"
    description: ClassVar[str] = "..."
    name: str

@dataclass
class E002(LintErrorBase):
    code: ClassVar[str] = "E002"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Type mismatch: expected '{expected}', got '{actual}'"
    description: ClassVar[str] = "..."
    expected: str; actual: str

# ... (all 15 variants follow the same pattern)

LintError = E001 | E002 | E003 | E004 | E005 | E006 | E007 | E008 | E009 | E010 | W001 | W002 | W003 | W004 | W005
```

Usage:
```python
err = E001("Moter_Run")
err.code       # "E001"
err.severity   # "error"
err.message    # "Undefined tag reference 'Moter_Run'"
err.description  # long prose explanation

match err:
    case E001(name=n): print(f"undefined: {n}")
    case W002(rung=r): print(f"unreachable: {rung}")
```

### RLL Domain Models

```python
@dataclass
class Operand:
    value: str                        # tag name, literal "42", or wildcard "?"
    type_hint: str | None = None      # filled by type resolution pass

@dataclass
class Instruction:
    opcode: str
    operands: list[Operand]
    branch: list[list[Instruction]] | None = None  # parallel branches in [...]
    is_output_branch: bool = False

@dataclass
class ParsedRung:
    number: int
    text: str                         # raw CDATA
    instructions: list[Instruction]
    output_branches: list[list[Instruction]]
```

### ST Domain Models

Full ST expression AST — needed so checks can walk tag references uniformly.

```python
# --- Expressions ---
@dataclass
class StBinaryOp:
    left: StExpression
    op: str                           # "+", "-", "*", "/", "=", "<>", "<", ">",
                                      # "<=", ">=", "and", "or"
    right: StExpression

@dataclass
class StUnaryOp:
    op: str                           # "-", "not"
    operand: StExpression

@dataclass
class StLiteral:
    value: int | float | str | bool

@dataclass
class StTagRef:
    path: TagPath

StExpression = StBinaryOp | StUnaryOp | StLiteral | StTagRef | StCall

# --- Statements ---
@dataclass
class StAssignment:
    target: TagPath
    expression: StExpression
    line: int

@dataclass
class StCall:
    name: str
    args: list[StExpression]
    line: int

@dataclass
class StIf:
    condition: StExpression
    body: list[StStatement]
    elsif_pairs: list[tuple[StExpression, list[StStatement]]]
    else_body: list[StStatement]
    line: int

@dataclass
class StCase:
    expression: StExpression
    cases: list[tuple[list[StExpression], list[StStatement]]]
    else_body: list[StStatement]
    line: int

@dataclass
class StFor:
    variable: TagPath
    start: StExpression
    end: StExpression
    step: StExpression | None         # "by" clause
    body: list[StStatement]
    line: int

@dataclass
class StWhile:
    condition: StExpression
    body: list[StStatement]
    line: int

@dataclass
class StRepeat:
    body: list[StStatement]
    until: StExpression
    line: int

@dataclass
class StJsr:
    routine_name: str
    args: list[StExpression]
    line: int

@dataclass
class StExit:
    line: int

@dataclass
class StReturn:
    line: int

StStatement = (
    StAssignment | StIf | StCase | StFor | StWhile | StRepeat
    | StCall | StJsr | StExit | StReturn
)

@dataclass
class StProgram:
    statements: list[StStatement]
```

### CheckFn — Unified Check Signature

Every check has the same interface. The routine router has already dispatched
RLL vs ST parsing, so checks consume `Routine` without caring about the type.

```python
CheckFn = Callable[[Routine, SymbolTable, Location], list[Diagnostic]]
```

### Check Registration

Checks are registered via a module-level `register()` decorator in `pipeline/analyze.py`:

```python
@register
def e001_undefined_tag(routine: Routine, symbols: SymbolTable, loc: Location) -> list[Diagnostic]:
    ...
```

The global `_registry` list collects all decorated functions at import time.
`analyze()` iterates `_registry` and calls each check for every program/routine pair.
Tests manage isolation via `analyze._registry.clear()` in setup.
```

### extract_tag_refs — The Bridge Between RLL and ST

This is the single function that makes all 15 checks type-agnostic.
It walks parsed content and returns flat tag paths.

```python
def extract_tag_refs(routine: Routine) -> list[TagPath]:
    """Extract all tag references from a routine, regardless of type."""
    match routine.type:
        case "RLL":
            return [
                tp for rung in routine.rll_rungs
                for instr in rung.instructions + [
                    i for branch in rung.instructions
                    if branch.branch for i in branch.branch
                ]
                for op in instr.operands
                for tp in parse_tag_path(op.value)
                if op.value != "?"             # skip wildcards
            ]
        case "ST":
            return _extract_st_tag_refs(routine.st_body)
        case _:
            return []                          # FBD/SFC: no text to analyze


def _extract_st_tag_refs(program: Maybe[StProgram]) -> list[TagPath]:
    """Walk StProgram statements and collect all TagPaths."""
    match program:
        case Nothing:
            return []
        case Some(prog):
            refs: list[TagPath] = []
            _walk_statements(prog.statements, refs)
            return refs


def _walk_statements(stmts: list[StStatement], acc: list[TagPath]) -> None:
    for stmt in stmts:
        match stmt:
            case StAssignment(target=tag):
                acc.append(tag)
                _walk_expression(stmt.expression, acc)
            case StCall(args=args):
                for a in args:
                    _walk_expression(a, acc)
            case StIf(condition=c, body=b, elsif_pairs=ep, else_body=eb):
                _walk_expression(c, acc)
                _walk_statements(b, acc)
                for _, elsif_body in ep:
                    _walk_statements(elsif_body, acc)
                _walk_statements(eb, acc)
            case StFor(variable=v, start=s, end=e, step=st, body=b):
                acc.append(v)
                _walk_expression(s, acc)
                _walk_expression(e, acc)
                if st: _walk_expression(st, acc)
                _walk_statements(b, acc)
            case StWhile(condition=c, body=b):
                _walk_expression(c, acc)
                _walk_statements(b, acc)
            case StRepeat(body=b, until=u):
                _walk_statements(b, acc)
                _walk_expression(u, acc)
            case StJsr(args=args):
                for a in args:
                    _walk_expression(a, acc)
            case _:
                pass  # StCase, StExit, StReturn — no tag refs to check


def _walk_expression(expr: StExpression, acc: list[TagPath]) -> None:
    match expr:
        case StTagRef(path=tag):
            acc.append(tag)
        case StBinaryOp(left=l, right=r):
            _walk_expression(l, acc)
            _walk_expression(r, acc)
        case StUnaryOp(operand=op):
            _walk_expression(op, acc)
        case StCall(args=args):
            for a in args:
                _walk_expression(a, acc)
        case _:
            pass  # StLiteral — no tag refs
```

### Routine — The Central Data Structure

```python
@dataclass
class Routine:
    name: str
    type: str                        # "RLL" | "ST" | "FBD" | "SFC"
    rll_rungs: list[ParsedRung]      # populated for RLL type
    st_body: Maybe[StProgram]        # populated for ST type, Nothing for others
    cdata: str                       # raw CDATA for debugging
```

### Tag, DataType, SymbolTable — Declaration-Side Models

```python
@dataclass
class Tag:
    name: str
    data_type: str                   # "DINT", "TIMER", "MyUDT", etc.
    dimensions: tuple[int, ...] = ()
    scope: str = "controller"        # "controller" | "program:<name>" | "aoi:<name>"
    description: str = ""

@dataclass
class Member:
    name: str
    data_type: str
    dimension: int = 0
    bit_number: int | None = None

@dataclass
class DataType:
    name: str
    family: str                      # "NoFamily", "StringFamily", etc.
    class_: str                      # "ProductDefined" | "User"
    members: list[Member]

@dataclass
class SymbolTable:
    controller_tags: dict[str, Tag]
    program_tags: dict[str, dict[str, Tag]]   # program_name → {tag_name → Tag}
    aoi_tags: dict[str, dict[str, Tag]]
    data_types: dict[str, DataType]

    def lookup(self, path: TagPath) -> Maybe[Tag]: ...
    def resolve_type(self, type_name: str) -> Maybe[DataType]: ...
    def scope_for(self, program: str) -> Scope: ...
```

---

## Research Findings (May 2026)

### Library Audit Summary

| Library | Stars | Status | Maturity | Key Finding |
|---------|-------|--------|----------|-------------|
| **jvalenzuela/l5x** v1.7 | 53 | Production/Stable (Mar 2026) | High | **Gap**: Exposes `controller.tags`, `programs[n].tags`, `modules` but does NOT expose `DataTypes`, `AddOnInstructionDefinitions`, or `Routine.RLLContent` as first-class model objects. Tag VALUE parsing is excellent (Decorated/L5K formats, struct/array/bit access). For structural metadata (type defs, AOIs, programs), must use ElementTree directly or the library's internal XML DOM. |
| **hutcheb/acd** v0.2a8 | 76 | Active (Mar 2026) | High | Full L5X element model in `acd/l5x/elements.py`: Controller, Program, Routine, Rung, Tag, DataType, Member, AOI, Parameter, Module, Port, etc. Built-in struct defs (TIMER, COUNTER, CONTROL) confirmed. ACD-to-L5X export recently added. **Excellent reference for domain model design.** |
| **alairjunior/l5x2c** | 11 | Archived (2019) | Low | PLY-based RLL parser covering ~25 instructions. Branch handling (parallel OR) and tag resolution are well-done. Grammar structure transfers 1:1 to Lark. Cant use as-is (PLY, unmaintained) but grammar is solid reference. |
| **benmusson/l5x-schema** | N/A | Static (archived) | High | XSD files for v32-v38 already cloned as submodule. Covers all XML structural constraints. Ready for validation via `xmlschema` library. |
| **tnunnink/L5Sharp** (C#) | 95 | Active | High | 46 test L5X files available. Strongly-typed query API is reference for symbol table design. Test data files already in use as baselines. |
| **mcp (Python SDK)** v1.25.0 | 23K | Official Anthropic SDK | Production | `FastMCP` class with tool/resource/prompt support. Transports: stdio, SSE, Streamable HTTP. MIT license. Python 3.10+. Well-suited for MCP server. |

### Key Architectural Decision: XML Adapter Strategy

**The `jvalenzuela/l5x` library does NOT expose DataTypes or AOI definitions as model attributes.** Its public API (`controller.tags`, `programs[n].tags`, `modules[n]`) covers tag value access but not structural metadata. Therefore the adapter layer is split:

1. **Structural XML parsing** (tags, data types, programs, routines, AOIs, tasks): Python `xml.etree.ElementTree` — stdlib, no dependency, handles all L5X structural XML.
2. **Tag value parsing** (for W004 Timer PRE value check, etc.): `l5x` library handles the complex Decorated/L5K data parsing.
3. **XSD validation** (optional): `xmlschema` library against `references/l5x-schema/`.

This is actually *lower risk* than depending entirely on `l5x` since ElementTree is built-in and XSD provides structural validation.

### Existing Codebase State

- `pyproject.toml`: Has `lark`, `l5x`, `returns` as deps. **Note**: `[tool.lint]` is non-standard — should be `[tool.ruff.lint]`.
- `tests/conftest.py`: Path setup only (5 lines).
- `tests/test_data_inventory.py`: 3 tests — file existence, per-code coverage assertion, XML validity.
- **14 valid L5X files**: projects (Simple, Test, Empty, ACDTestsWithAOI, ex1), routines (Main, ST), rungs (Rung0_from_Main, Message_Rung), instructions (aoi_Test), data types (SimpleType, ComplexType, ArrayType). Good coverage of real-world constructs.
- **14 invalid L5X files**: One per E/W code (E001-E010, W001-W005). Each triggers exactly one diagnostic.
- **Source code**: No `l5x_lint/` package yet — implementation from scratch.
- **Submodules**: All 5 reference repos cloned (`references/l5x2c`, `references/l5x`, `references/acd`, `references/L5Sharp`, `references/l5x-schema`).

---

## Checks to Implement

```
ERRORS (block simulation):
  E001  Undefined tag reference           XIC(Moter_Run) — tag doesn't exist          ✅
  E002  Type mismatch                     TON(MyDINT,...) — DINT ≠ TIMER              ✅
  E003  Missing AOI definition            Calling My_AOI, not defined                 ✅
  E004  Invalid JSR target                JSR(NoSuchRoutine,0)                        ✅
  E005  Invalid UDT member access         Tag.NonExistent                             ✅
  E006  Array index out of bounds         Arr[10] on Arr[10] (0-indexed)              ✅
  E007  Duplicate tag name in scope                                                   ✅
  E008  AOI circular dependency           AOI_A → AOI_B → AOI_A                      ✅
  E009  Wrong operand count               XIC() with no args                          ✅
  E010  Cross-scope tag violation         Program tag used in another program         ✅

WARNINGS (allow simulation):
  W001  Unused tag declared                                                           ✅
  W002  Unreachable rung                  AFI as first instruction                    ✅
  W003  Output never driven               Used in XIC, never in OTE/OTL/OTU          ✅
  W004  Timer PRE never set               TON with PRE still 0                       ✅
  W005  Shadowed tag name                 Prog tag hides ctrl tag                    ✅
```

---

## Structured Output

```json
{
  "passed": false,
  "error_count": 2,
  "warning_count": 1,
  "diagnostics": [{
    "code": "E001",
    "severity": "error",
    "location": { "program": "MainProgram", "routine": "MainRoutine", "rung": 4 },
    "message": "Undefined tag reference 'Moter_Run'",
    "hint": "Did you mean 'Motor_Run'? (edit distance: 1)",
    "fix_suggestion": "Change 'Moter_Run' to 'Motor_Run', or declare tag 'Moter_Run' as BOOL"
  }]
}
```

The `fix_suggestion` field lets the agent fix without another LLM call for simple errors.

---

## Implementation Strategy

### Revised Architecture

| Layer | Approach | Dependencies | Risk |
|-------|----------|-------------|------|
| **L5X XML → Domain Model** | ElementTree for structural (tags, types, programs, AOIs, routines). `l5x` library for tag value parsing (W004). | `l5x` (optional tag values), stdlib `xml.etree.ElementTree` | **Low** — ElementTree is stdlib, L5X XML is well-structured |
| **XSD Structural Validation** | `xmlschema` library + `references/l5x-schema/` XSD files | `xmlschema`, `l5x-schema` submodule | **Low** — XSD files are frozen specs |
| **RLL Neutral Text Parsing** | Lark LALR(1) grammar — new grammar covering ~120 instructions | `lark` | **Medium** — grammar complexity, 120+ opcodes |
| **ST Text Parsing** | Lark LALR(1) grammar — IEC 61131-3 with Rockwell dialect | `lark` | **Low** — well-defined EBNF, same infrastructure as RLL |
| **Routine Type Router** | `match` on `Routine.type`, dispatches to RLL/ST parser or skips FBD/SFC | None | **Low** — straightforward dispatch |
| **Symbol Table** | Pure construction from domain model. Scope-aware lookup (controller → program). | None | **Low** — textbook symbol table |
| **Type System** | Data-driven: opcode → (position → type_constraint) matrix | None | **Medium** — data entry for 120+ instructions |
| **15 Checks (E001-W005)** | One pure function per check | `returns` | **Low-Medium** — most are straightforward, checks are content-type-agnostic |
| **MCP Server** | `FastMCP` exposing 4 tools | `mcp` | **Low** — well-documented SDK |
| **Pipeline** | `flow()` composition | `returns` | **Low** — already designed in detail |

### L5X XML Adapter Detail

The adapter layer handles these XML sections:

```xml
<!-- Tags (controller-scoped) -->
<Controller>
  <Tags>
    <Tag Name="MyTag" TagType="Base" DataType="DINT" Dimensions="10" .../>
  </Tags>
</Controller>

<!-- Data type definitions -->
<DataTypes>
  <DataType Name="MyUDT" Family="NoFamily" Class="User">
    <Members>
      <Member Name="Value" DataType="DINT" Dimension="0" .../>
    </Members>
  </DataType>
</DataTypes>

<!-- Programs with routines and rungs -->
<Programs>
  <Program Name="MainProgram">
    <Tags>...</Tags>
    <Routines>
      <Routine Name="MainRoutine" Type="RLL">
        <RLLContent>
          <Rung Number="0">
            <Text><![CDATA[XIC(Start)OTE(Run);]]></Text>
          </Rung>
        </RLLContent>
      </Routine>
    </Routines>
  </Program>
</Programs>

<!-- AOI definitions -->
<AddOnInstructionDefinitions>
  <AddOnInstructionDefinition Name="MyAOI" Revision="1.0">
    <Parameters>...</Parameters>
    <LocalTags>...</LocalTags>
    <Routines>...</Routines>
  </AddOnInstructionDefinition>
</AddOnInstructionDefinitions>
```

The adapter maps these into typed dataclasses:

```python
@dataclass
class L5XProject:
    schema_revision: str
    software_revision: str
    controller: Controller

@dataclass
class Controller:
    name: str
    processor_type: str | None
    data_types: list[DataType]       # from <DataTypes>
    tags: list[Tag]                  # controller-scoped tags
    programs: list[Program]          # from <Programs>
    tasks: list[Task]
    aois: list[AOI]                  # from <AddOnInstructionDefinitions>
    modules: list[Module]

# Routine with type-aware parsed content
@dataclass
class Routine:
    name: str
    type: str                        # "RLL" | "ST" | "FBD" | "SFC"
    rll_rungs: list[ParsedRung]      # populated for RLL type
    st_body: Maybe[StProgram]        # populated for ST type, Nothing for others
    cdata: str                       # raw CDATA for debugging

# ST parsed program
@dataclass
class StProgram:
    statements: list[StStatement]

StStatement = (
    StAssignment
    | StIf
    | StCase
    | StFor
    | StWhile
    | StRepeat
    | StCall
    | StJsr
    | StExit
    | StReturn
)

@dataclass
class StAssignment:
    target: TagPath
    expression: StExpression
    line: int

@dataclass
class StCall:
    name: str
    args: list[StExpression]
    line: int

@dataclass
class StIf:
    condition: StExpression
    body: list[StStatement]
    elsif_pairs: list[tuple[StExpression, list[StStatement]]]
    else_body: list[StStatement]
    line: int
```

**Implementation plan for `adapter.py`**:
1. Parse XML with `xml.etree.ElementTree.parse()` or `fromstring()`
2. Walk the tree using XPath-like `findall()`/`find()`
3. Construct dataclass instances
4. Wrap in `Result` using `@safe` decorator

No need for `pydantic` — dataclasses are sufficient for pure data.

### Routine Type Routing

The `parse_all_routine_content` pipeline step dispatches by `Routine.type`:

```python
def parse_routine_content(routine: Routine) -> Result[Routine, LintError]:
    """Parse a routine's CDATA based on its type field."""
    match routine.type:
        case "RLL":
            result = parse_rll(routine.cdata)
            return result.map(lambda rungs: replace(routine, rll_rungs=rungs))
        case "ST":
            result = parse_st(routine.cdata)
            return result.map(
                lambda prog: replace(routine, st_body=Some(prog))
            )
        case _:
            # FBD/SFC — graphical XML, no text to parse. Skip.
            return Success(routine)
```

Routine type is read from the XML attribute:

```xml
<Routine Name="MainRoutine" Type="RLL">     <!-- RLL → rung_parser -->
<Routine Name="StRoutine" Type="ST">         <!-- ST  → st_parser    -->
<Routine Name="FbdRoutine" Type="FBD">       <!-- FBD → skip         -->
<Routine Name="SfcRoutine" Type="SFC">       <!-- SFC → skip         -->
```

All FBD/SFC routines pass through the pipeline unmodified — they contribute
no tag references to the analysis, which means E001/E002/E005 are blind to
their contents. This is acceptable for v1: FBD/SFC analysis requires graph
parsing (wire tracing, block connections) and is tracked as a separate
architectural effort. The symbol table is built from tag declarations, not
tag usages, so FBD/SFC routines are still fully analyzed for Declaration-side
checks (W001, E007, E010) via their program's `<Tags>`.

### RLL Grammar: l5x2c → Lark Migration

The reference grammar (25 instructions, PLY) maps cleanly to Lark:

| l5x2c (PLY) | Lark Equivalent | Status |
|-------------|----------------|--------|
| `input_instruction : XIC LPAR parameter RPAR` | `input_instruction : OPCODE LPAR params RPAR` | Generalized — same pattern for all 120+ instructions |
| Branch: `[INPUT_LEVEL]` → `LBRA ... RBRA` | Same syntax | Direct 1:1 mapping |
| Tag: complex regex with member/index | `TAG_NAME` token + grammar rules | Simplified in Lark |
| CPT: expression with `+ - * / ( )` | `cpt_expression : ...` | Same structure |

The Lark grammar from `docs/parser-spec.md §2.2` is already well-designed. Key verification points:
- Terminal opcode list: 120+ opcodes as a single `OPCODE` token with case-insensitive matching
- Branch structure: parallel OR (comma-separated) within `[...]`
- Tag name regex: `[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*(\[\d+\])*`
- Wildcard `?` operand for TON/TOF/RTO/CTU/CTD PRE/ACC positions

### RLL Parser Verification (New)

Before implementing all checks, write a standalone RLL parser verification suite:

```python
# tests/test_rll_parser.py
RLL_CASES = [
    ("XIC(Start)OTE(Run);", True),
    ("XIC(A)[XIO(B),XIO(C)]OTE(D);", True),   # branch
    ("TON(Timer1,?,?);", True),                  # wildcards
    ("XIC()OTE(D);", False),                     # E009 — missing operand
    ("MOV(42,Dest);", True),
    ("CPT(Dest, A+B*C);", True),                 # expression
    ("XIC(Moter_Run)OTE(Motor);", True),          # typo is syntactically valid
]
```

This catches grammar issues before any check implementation.

### ST (Structured Text) Grammar

ST is parsed with Lark LALR(1), same infrastructure as RLL. The grammar targets IEC 61131-3 with Rockwell's dialect:

| Feature | IEC 61131-3 | Rockwell Dialect |
|---------|-------------|-----------------|
| Keywords | `IF, THEN, ELSIF, ELSE, END_IF` | `if, then, elsif, else, end_if` (lowercase) |
| Assignment | `A := B;` | Same — `:=` operator |
| Function calls | `TON(IN:=, PT:=)` | `TON(Timer1, ?, ?)` — positional args, `?` wildcard |
| JSR | N/A | `JSR(RoutineName, Param1);` |
| Comments | `(* *)` and `//` | Both supported |
| Type punning | No standard | Implicit — `DINT := BOOL` passes checks |

#### Grammar Structure

```
st_program:  statement+
statement:   assignment
           | if_statement
           | case_statement
           | for_loop
           | while_loop
           | repeat_loop
           | function_call ";"
           | exit_statement
           | return_statement
           | jsr_call

assignment:  tag_path ":=" expression ";"

if_statement:
  "if" expression "then" statement+
  ("elsif" expression "then" statement+)*
  ("else" statement+)?
  "end_if"

case_statement:
  "case" expression "of"
    case_element+
  ("else" statement+)?
  "end_case"

case_element:  expression ("," expression)* ":" statement+

for_loop:      "for" tag_path ":=" expression "to" expression
               ("by" expression)? "do" statement+ "end_for"

function_call: IDENTIFIER "(" (expression ("," expression)*)? ")"

expression:    or_expr
or_expr:       and_expr ("or" and_expr)*
and_expr:      compare_expr ("and" compare_expr)*
compare_expr:  add_expr (("=" | "<>" | "<" | ">" | "<=" | ">=") add_expr)?
add_expr:      mul_expr (("+" | "-") mul_expr)*
mul_expr:      unary_expr (("*" | "/") unary_expr)*
unary_expr:    ("-" | "not")* atom
atom:          tag_path | NUMBER | function_call | "(" expression ")"
```

#### Shared Infrastructure with RLL

- **Same symbol table** — ST tag refs go through identical `scope.lookup()` path
- **Same type system** — `TON(Timer1, ?, ?)` in ST resolves the same type rules as in RLL
- **Same checks** — E001 (undefined tag), E002 (type mismatch), E005 (invalid member), E009 (operand count) all apply
- **Same `Diagnostic` model** — location just uses `(program, routine, line)` instead of `rung`

#### Transformer Design

```python
class StTransformer(Transformer):
    def assignment(self, items) -> StAssignment:
        tag_path, expr = items
        return StAssignment(tag_path, expr)

    def if_statement(self, items) -> StIf:
        # items: [condition, *body_blocks, (elsif_pairs, else_block)?]
        ...

    def function_call(self, items) -> StCall:
        name, *args = items
        return StCall(str(name), args)
```

#### Extraction Flow

```
adapter.py → finds <Routine Type="ST">
           → reads <STContent><![CDATA[...]]></STContent>
           → calls st_parser.parse(cdata) → StProgram
           → stores in Routine.st_body (Maybe[StProgram])
```

The `parse_all_routine_content` pipeline step dispatches by `Routine.type`:

```python
def parse_routine_content(
    routine: Routine
) -> Result[Routine, LintError]:
    match routine.type:
        case "RLL": return bind(parse_rll)(routine.rll_cdata)
        case "ST":  return bind(parse_st)(routine.st_cdata)
        case _:     return Success(routine)  # FBD/SFC: skip, no text analysis
```

### Instruction Operand Data

Instruction operand rules are encoded as **data**, not code:

```python
# type_system.py
@dataclass
class OperandRule:
    position: int       # 0-based operand index
    types: list[str]    # accepted types: ["BOOL"], ["TIMER"], ["numeric", "ANY"], ...

@dataclass
class InstructionRule:
    opcode: str
    min_operands: int
    max_operands: int
    operand_rules: list[OperandRule]
    category: str       # "input", "output", "both"

# Instruction catalog — ~120 entries
INSTRUCTION_RULES: dict[str, InstructionRule] = {
    "XIC":  InstructionRule("XIC", 1, 1, [OperandRule(0, ["BOOL"])], "input"),
    "XIO":  InstructionRule("XIO", 1, 1, [OperandRule(0, ["BOOL"])], "input"),
    "OTE":  InstructionRule("OTE", 1, 1, [OperandRule(0, ["BOOL"])], "output"),
    "TON":  InstructionRule("TON", 3, 3, [
        OperandRule(0, ["TIMER"]),
        OperandRule(1, ["wildcard"]),   # PRE — ? is valid
        OperandRule(2, ["wildcard"]),   # ACC — ? is valid
    ], "output"),
    "MOV":  InstructionRule("MOV", 2, 2, [
        OperandRule(0, ["any"]),        # source: any type
        OperandRule(1, ["same_as_0"]),  # dest: must match source
    ], "output"),
    "JSR":  InstructionRule("JSR", 1, 10, [
        OperandRule(0, ["routine_name"]),
    ], "output"),
    "AFI":  InstructionRule("AFI", 0, 0, [], "input"),
    # ... 115+ more entries
}
```

Source data comes from:
1. l5x2c operand tables (~25 entries, verified reference)
2. Rockwell 1756-rm084 PDF (ground truth for all ~120 instructions)
3. Cross-referenced with `hutcheb/acd` element model

### Built-In Type Registry

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
        Member("PRE", "DINT"), Member("ACC", "DINT"),
        Member("EN", "BOOL"), Member("TT", "BOOL"), Member("DN", "BOOL"),
    ]),
    "COUNTER": DataType("COUNTER", "NoFamily", "ProductDefined", [
        Member("PRE", "DINT"), Member("ACC", "DINT"),
        Member("CU", "BOOL"), Member("CD", "BOOL"), Member("DN", "BOOL"),
        Member("OV", "BOOL"), Member("UN", "BOOL"),
    ]),
    "CONTROL": DataType("CONTROL", "NoFamily", "ProductDefined", [
        Member("LEN", "DINT"), Member("POS", "DINT"),
        Member("EN", "BOOL"), Member("EU", "BOOL"), Member("DN", "BOOL"),
        Member("EM", "BOOL"), Member("ER", "BOOL"), Member("UL", "BOOL"),
        Member("IN", "BOOL"), Member("FD", "BOOL"),
    ]),
    "STRING":  DataType("STRING", "StringFamily", "ProductDefined", [
        Member("LEN", "DINT"), Member("DATA", "STRING"),
    ]),
    "MESSAGE": DataType("MESSAGE", "NoFamily", "ProductDefined", []),
}
```

Confirmed from `hutcheb/acd` elements.py and `docs/initial-data-collection.md`.

### Testing Strategy — Expanded

#### Unit Tests (per check)

```python
# tests/test_e001_undefined_tag.py
def test_undefined_tag_detected():
    scope = SymbolTable([Tag("Motor_Run", "BOOL")])
    rung = ParsedRung(0, "XIC(Moter_Run)", [
        Instruction("XIC", [Operand("Moter_Run")])
    ], [])
    diags = check_undefined_tags([rung], scope)
    assert len(diags) == 1
    assert diags[0].code == "E001"
    assert "Moter_Run" in diags[0].message
    assert "Motor_Run" in diags[0].hint  # edit distance = 1

def test_defined_tag_no_error():
    scope = SymbolTable([Tag("Motor_Run", "BOOL")])
    rung = ParsedRung(0, "XIC(Motor_Run)", [
        Instruction("XIC", [Operand("Motor_Run")])
    ], [])
    diags = check_undefined_tags([rung], scope)
    assert len(diags) == 0
```

#### Integration Tests (per L5X file)

```python
# tests/test_integration.py
@pytest.mark.parametrize("code, file", [
    ("E001", "E001_undefined_tag.L5X"),
    ("E002", "E002_type_mismatch.L5X"),
    # ... all 14 codes
])
def test_invalid_file_triggers_diagnostic(code, file):
    result = run_analysis(INVALID_DIR / file)
    assert result.passed == (code.startswith("W"))  # warnings don't fail
    codes = [d.code for d in result.diagnostics]
    assert code in codes

@pytest.mark.parametrize("file", [
    "projects/Simple.L5X", "projects/ACDTestsWithAOI.L5X",
    "routines/Main.L5X", "instructions/aoi_Test.L5X",
])
def test_valid_file_no_diagnostics(file):
    result = run_analysis(VALID_DIR / file)
    assert len(result.diagnostics) == 0
```

#### RLL Parser Tests (new)

```python
# tests/test_rll_parser.py
RLL_CASES = [
    "XIC(Start)OTE(Run);",
    "XIC(A)[XIO(B),XIO(C)]OTE(D);",       # parallel branch
    "TON(Timer1,?,?);",                     # wildcards
    "MOV(42,Dest);",
    "CPT(Dest, A+B*C);",                   # expression
    "XIC(A)[XIO(B),XIO(C)]OTE(D)[OTL(E)];", # output branches
    "AFI;",                                 # zero-operand
    "JSR(MyRoutine,Param1,Param2);",        # multi-param JSR
]

@pytest.mark.parametrize("text", RLL_CASES)
def test_parse_valid_rll(text):
    result = parse_rll(text)
    assert isinstance(result, ParsedRung)

INVALID_RLL = [
    ("XIC()OTE(D);", "missing_operand"),
    ("XIC(A, B)OTE(D);", "too_many_operands"),
    (";", "empty"),
    ("INVALID_OP(Tag);", "unknown_opcode"),
]

@pytest.mark.parametrize("text,reason", INVALID_RLL)
def test_parse_invalid_rll(text, reason):
    result = parse_rll(text)
    assert isinstance(result, Failure)

#### ST Parser Tests (new)

```python
# tests/test_st_parser.py
ST_VALID = [
    ("x := 42;", "simple_assign"),
    ("x := y + 1;", "add"),
    ("if x then y := 1; end_if", "if_block"),
    ("if x then y := 1; else y := 2; end_if", "if_else"),
    ("if x then y := 1; elsif z then y := 2; end_if", "elsif"),
    ("for i := 1 to 10 do x := x + 1; end_for", "for_loop"),
    ("while x < 10 do x := x + 1; end_while", "while_loop"),
    ("TON(Timer1, ?, ?);", "timer_call_rll_style"),
    ("JSR(MyRoutine, Param1);", "jsr_call"),
    ("x := (a + b) * c;", "paren_expr"),
    ("if x and not y then z := 1; end_if", "compound_condition"),
]

@pytest.mark.parametrize("text,reason", ST_VALID)
def test_parse_valid_st(text, reason):
    result = parse_st(text)
    assert isinstance(result, StProgram)
    assert len(result.statements) >= 1

ST_INVALID = [
    ("x := ;", "incomplete_assign"),
    ("if x then end_if", "empty_if_body"),
    ("x := 1 +;", "trailing_op"),
    ("case x of end_case", "empty_case"),
]

@pytest.mark.parametrize("text,reason", ST_INVALID)
def test_parse_invalid_st(text, reason):
    result = parse_st(text)
    assert isinstance(result, Failure)
```

---

## Dependency Verification

### `jvalenzuela/l5x` — API Surface Confirmed

From README and source analysis:
- `l5x.Project(path)` → `prj.controller` (Controller), `prj.programs`, `prj.modules`
- `controller.tags` → tag scope with dict-like access by name
- `programs['name'].tags` → program-scoped tag scope
- `tag.data_type` → string like "DINT", "TIMER"
- `tag.value` → Python native value (int, float, dict for structs, list for arrays)
- `tag['member']` → member access for struct types
- `tag[3]` → bit access for integers
- `tag.shape` → tuple of array dimensions
- `tag.description` → string or None
- `tag.alias_for` → string or None (alias tags only)
- **Not exposed**: `controller.data_types`, `controller.add_on_instruction_definitions`, `program.routines`, `routine.rungs`

**Implication**: Adapter uses ElementTree for structural data, `l5x` for tag value parsing only. This is fine.

### `mcp` Python SDK — Capability Confirmed

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("l5x-lint")

@mcp.tool()
def validate_l5x(l5x_xml: str) -> AnalysisResult:
    """Validate an L5X XML file and return structured diagnostics."""
    ...

@mcp.tool()
def suggest_fixes(diagnostic: Diagnostic) -> list[FixSuggestion]:
    """Get fix suggestions for a diagnostic."""
    ...
```

Transport: `Streamable HTTP` for agent integration. `stdio` for local CLI.

---

## Revised Confidence Assessment (Post-Research)

| Component | Confidence | Evidence |
|-----------|-----------|----------|
| **XML Adapter (ElementTree)** | 95% | ElementTree is stdlib; L5X XML is well-structured; XSD available for validation |
| **Symbol Table** | 95% | Textbook design; scope hierarchy is clear; tag model is well-defined |
| **Lark RLL Grammar** | 85% | l5x2c proves the approach works; Lark spike validated 24/25 cases. Risk: ~120 opcodes need correct tag name parsing edge cases (communication tags, expressions in CPT). CPT expression parsing needs precedence grammar port. |
| **Lark ST Grammar** | 90% | IEC 61131-3 EBNF is well-defined; Lark handles it naturally. Rockwell dialect is a strict subset (lowercase keywords, positional args, JSR). Infers 15/15 checks identically to RLL — tag refs are tag refs regardless of syntax. |
| **Routine Type Router** | 95% | Simple `match` on `Routine.type` string. FBD/SFC are XML-only, skipped by text parsers. No complexity. |
| **Type System Data** | 85% | ~120 instruction rules from 1756-rm084 + l5x2c + acd cross-reference. Data-entry effort, but well-defined format reduces error |
| **15 Checks (E001-W005)** | 100% | All 15 checks implemented and tested (329 total tests). Simple checks (E004/E007/W005) done first, medium (E005/E006/E009/E010/W003/W001) next, complex (E002/E003/E008/W004) last. E008 uses DFS for cycle detection. W004 flags any timer used with TON/TOF/RTO (full PRE parsing requires l5x tag value access). |
| **MCP Server** | 95% | FastMCP API is documented and simple; 4 tools only |
| **Test Data** | 85% | 14 valid + 14 invalid files exist. L5Sharp provides 33+ more untapped files (FBD.L5X, SFC.L5X, ST.L5X, LotOfTags.L5X). ~5 custom rung files needed for instruction coverage gaps. Need ST-specific valid/invalid files. |
| **Edge Case Coverage** | 80% | RLL spike covered nested branches, wildcards, comm tags. ST plan covers loops, conditionals, JSR. Gaps: safety tags, produced/consumed tags, module-scoped tags, string manipulation instructions. |

### Remaining Risks

1. **RLL grammar: communication tags** (`CIP:0:Tag.Member`) — l5x2c supports these; our grammar must too. This adds complexity to the tag regex.
2. **CPT expression parsing** — l5x2c has a precedence-based expression grammar that handles `+`, `-`, `*`, `/`, and `()`. Needs to be ported to Lark.
3. **Timer PRE value access via l5x library** — only needed for W004. Confirmed the library supports `tag['PRE'].value`.
4. **Valid test file coverage** — some valid files have no rungs or simple rungs only. L5Sharp's LotOfTags.L5X (3.1MB, 10K tags) and 5 custom rung files will close this gap.
5. **ST CDATA in L5X XML** — need to confirm L5X `<STContent>` CDATA format vs `<RLLContent>`. ACD library confirms ST routines wrap text in `<STContent><![CDATA[...]]></STContent>` same as RLL.

---

## Toolchain

| Tool | Purpose |
|------|---------|
| `uv` | Package management (replaces pip/poetry/virtualenv) |
| `ruff` | Code formatting + linting |
| `returns` | `Result`, `Maybe`, `flow`, `bind` for functional composition |
| `lark` | RLL neutral text parser generator |
| `jvalenzuela/l5x` | L5X tag value parsing (optional, for W004) |
| `xmlschema` | XSD validation (optional, for structural checks) |
| `mcp` | MCP protocol server (Anthropic SDK) |
| `pytest` | Test framework |

### uv Commands

```powershell
uv sync                           # Install all deps from pyproject.toml
uv add <package>                  # Add runtime dependency
uv add --dev <package>            # Add dev dependency
uv run python -m l5x_lint ...    # Run module in env
uv run pytest tests/ -v          # Run tests
uv run pytest tests/ --cov       # Run with coverage
uvx ruff check .                  # Lint (ephemeral)
uvx ruff format .                 # Format
```

---

## Existing OSS Referenced

| Repo | What for |
|---|---|
| `jvalenzuela/l5x` | Tag value parsing (Decorated/L5K data) |
| `alairjunior/l5x2c` | RLL grammar reference, operand type tables |
| `tnunnink/L5Sharp` | 46 test L5X files, C# object model reference |
| `hutcheb/acd` | Full L5X element model, built-in struct definitions |
| `benmusson/l5x-schema` | XSD schemas for structural validation |
| Rockwell 1756-rm084 | Ground truth for instruction semantics |

---

## MCP Tools Exposed

```
validate_l5x(l5x_xml: str) → AnalysisResult
check_tag_references(l5x_xml: str) → list[TagRefError]
get_cross_references(l5x_xml: str, tag_name: str) → CrossRefResult
suggest_fixes(diagnostic: Diagnostic) → list[FixSuggestion]
```

---

## Module Structure — Implementation Status

```
l5x_lint/
  domain/                        # ✅ DONE — Pure data types, zero dependencies
    __init__.py                  #     Re-exports all public types
    models.py                    #     Tag, DataType, Routine, TagPath, Location
    diagnostics.py               #     Diagnostic, AnalysisResult, FixSuggestion
    errors.py                    #     LintError (15 self-describing variants with .code, .severity, .message, .description)
    rll_models.py                #     ParsedRung, Instruction, Operand
    st_models.py                 #     StProgram, StStatement, StExpression AST
    symbol_table.py              # ⏳ PENDING — SymbolTable, Scope (pure query methods)
    type_system.py               # ⏳ PENDING — Type compatibility matrix, member resolution
    tag_refs.py                  # ⏳ PENDING — extract_tag_refs (RLL + ST dispatch)

  checks/                        # ✅ DONE — all 15 checks
    __init__.py
    opcodes.py                   #     Shared opcode catalog (150+ opcodes)
    tag_refs.py                  #     Shared tag reference extraction (RLL + ST)
    e001_undefined_tag.py        # ✅ 44 tests
    e002_type_mismatch.py        # ✅ 8 tests
    e003_missing_aoi.py          # ✅ 6 tests
    e004_invalid_jsr.py          # ✅ 6 tests
    e005_invalid_member.py       # ✅ 5 tests
    e006_array_bounds.py         # ✅ 7 tests
    e007_duplicate_tag.py        # ✅ 3 tests
    e008_aoi_circular.py         # ✅ 3 tests
    e009_wrong_operand_count.py  # ✅ 7 tests
    e010_cross_scope.py          # ✅ 4 tests
    w001_unused_tag.py           # ✅ 4 tests
    w002_afi_rung.py             # ✅ 10 tests
    w003_output_never_driven.py  # ✅ 6 tests
    w004_timer_pre.py            # ✅ 6 tests
    w005_shadowed_tag.py         # ✅ 5 tests

  pipeline/                      # ✅ DONE — rung_parser + st_parser + symbols + analyze
    __init__.py
    analyze.py                   #     Compose all checks via flow(), register() decorator, 8 tests
    routine_router.py            #     Dispatch by Routine.type → RLL/ST parser, 11 tests
    symbols.py                   #     SymbolTable + build_symbol_table, 11 tests
    rung_parser.py               # ✅   Lark grammar + transformer → Result[list[ParsedRung]], 27 tests
    st_parser.py                 # ✅   Lark grammar + transformer → Result[StProgram], 35 tests

  infrastructure/                # ⏳ PENDING
    adapter.py                   #     ElementTree + l5x → domain models
    mcp_server.py                #     FastMCP server exposing MCP tools

tests/                           # Test folder mirrors src/ structure (329 tests)
  conftest.py                    # Path fixtures
  test_data_inventory.py         # Sanity checks on test data
  domain/                        # ✅ DONE — mirrors src/l5x_lint/domain/
  checks/                        # ✅ DONE — 124 tests across 15 check files
  pipeline/                      # ✅ DONE — see test_rung_parser.py (27), test_st_parser.py (35), test_routine_router.py (11), test_symbols.py (11), test_analyze.py (8)
    test_rung_parser.py          #     27 tests: parsing, branches, error handling
    test_st_parser.py            #     35 tests: assignments, if/for/while/repeat, calls, JSR, expressions, precedence, error handling
    test_models.py               #     TagPath, Location, Tag, DataType, Routine, ...
    test_diagnostics.py          #     Diagnostic, AnalysisResult, FixSuggestion
    test_errors.py               #     All 15 LintError variants, .code .severity .message .description
    test_rll_models.py           #     ParsedRung, Instruction, Operand
    test_st_models.py            #     StProgram, StStatement, StExpression AST
  data/valid/                    # Baseline L5X files
    projects/Simple.L5X, Test.L5X, Empty.L5X, ACDTestsWithAOI.L5X, ex1.L5X
    routines/Main.L5X, ST.L5X, FBD.L5X, SFC.L5X, Rung1_from_Main.L5X
    instructions/aoi_Test.L5X, Message_Rung.L5X, Rung0_from_Main.L5X
    types/SimpleType.L5X, ComplexType.L5X, ArrayType.L5X
    large/LotOfTags.L5X              # 3.1MB, 10K tags — stress test
    # +5 custom rung files (see Custom Test Data below)
  data/invalid/                  # 14 broken L5X files (one per code)
  data/custom/                   # Hand-crafted files targeting specific coverage gaps
    rungs_math.L5X               # ADD/SUB/MUL/DIV, all variants
    rungs_compare.L5X            # LES/NEQ/LEQ/GEQ/EQU/GRT
    rungs_prog_control.L5X       # JMP/LBL/MCR/JSR with params
    rungs_process.L5X            # SCL/PID/TON/TOF/RTO with real operands
    st_aoi_logic.L5X             # AOI with ST routine body
```

---

## Integration Context

```
Agent → l5x-forge:  generate_routine(...) → l5x_xml
Agent → l5x-lint:   validate_l5x(l5x_xml) → diagnostics
Agent → l5x-forge:  fix_errors(xml, diagnostics) → corrected xml
Agent → l5x-sim:    load + simulate + assert
```

---

## Packaging & Deployment

l5x-lint is a **pip-installable Python package** exposed as an MCP server.
It does NOT need Docker, Kubernetes, or any container orchestration.
The MCP protocol means any MCP host (Claude Desktop, Cursor, VS Code, custom agent)
can discover and invoke it over stdio or HTTP.

### Distribution Options

| Method | Command | Use Case |
|--------|---------|----------|
| **pip install (from source)** | `uv pip install -e .` | Dev, local testing |
| **pip install (from PyPI)** | `uv pip install l5x-lint` | CI/CD, production |
| **uvx (ephemeral)** | `uvx l5x-lint` | One-shot runs, no install needed |
| **Docker image** | `docker run l5x-lint ...` | Sandboxed/isolated environments |

### Primary Deployment: MCP Server via stdio

The simplest deployment — **no ports, no daemons, no Docker.**

```powershell
# Install once
uv pip install l5x-lint

# Run as MCP server (stdio transport)
python -m l5x_lint serve
```

The MCP host (Claude Desktop, VS Code, etc.) configures it like any other MCP tool:

```json
{
  "mcpServers": {
    "l5x-lint": {
      "command": "uvx",
      "args": ["l5x-lint"]
    }
  }
}
```

`uvx l5x-lint` downloads and runs on the fly — no install step.
The MCP host spawns the process, pipes stdin/stdout, and auto-discovers
the `validate_l5x`, `check_tag_references`, `get_cross_references`, and
`suggest_fixes` tools via the MCP ListTools handshake.

### Secondary Deployment: MCP Server via HTTP

For remote agent access (e.g., an agent running on a different machine):

```powershell
python -m l5x_lint serve --transport http --port 8080
```

The MCP host connects to `http://host:8080/` using Streamable HTTP transport.
This is useful when the PLC toolchain runs on a dedicated build server and
agents connect remotely.

### Tertiary Deployment: CLI Direct Invocation

```powershell
# Validate a single file
python -m l5x_lint validate program.L5X

# Validate from stdin
cat program.L5X | python -m l5x_lint validate -

# Validate from agent-generated XML string
python -m l5x_lint validate --xml "<RSLogix5000Content>...</RSLogix5000Content>"
```

Prints structured JSON to stdout. Useful for shell scripts, CI pipelines,
and pre-commit hooks.

### Docker (Optional)

Only needed for sandboxed environments where you can't install Python
or need to pin the exact runtime.

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN uv pip install l5x-lint
ENTRYPOINT ["uvx", "l5x-lint"]
```

```powershell
docker build -t l5x-lint .
docker run -i l5x-lint validate - < program.L5X
```

### CI/CD Integration

```yaml
# .github/workflows/lint.yml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: uvx l5x-lint validate --xml "$(cat exports/*.L5X)"
```

The linter exits non-zero if any errors are found, making it suitable
for gating merges.

### Summary

| Scenario | Transport | Command |
|----------|-----------|---------|
| Claude Desktop | stdio | `uvx l5x-lint` |
| VS Code | stdio | `uvx l5x-lint` |
| Remote agent (LAN) | HTTP | `python -m l5x_lint serve --transport http` |
| CI pipeline | CLI | `python -m l5x_lint validate file.L5X` |
| pre-commit hook | CLI | `python -m l5x_lint validate --stdin` |
| Docker sandbox | CLI | `docker run -i l5x-lint validate -` |

No compilation. No containers required. A single `uvx` invocation from
any MCP host is the intended primary path.
