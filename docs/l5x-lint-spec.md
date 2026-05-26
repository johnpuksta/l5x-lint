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
                     ┌──────────────────────┐
XML string ─────────►│  adapter.py           │
                     │  (l5x library wrapper)│
                     │  → Result[L5XProject] │
                     └──────────┬───────────┘
                                ▼
                     ┌──────────────────────┐
                     │  SymbolTable(project) │
                     │  (pure construction)  │
                     └──────────┬───────────┘
                                ▼
                     ┌──────────────────────┐
                     │  rung_parser.py       │
                     │  Lark → ParsedRung[]  │
                     │  → Result[ParsedRung] │
                     └──────────┬───────────┘
                                ▼
               ┌──────────────────────────────────┐
               │  checks/*.py                      │
               │  Each: (SymbolTable, Routine)     │
               │       → list[Diagnostic]          │
               │  Composed via flow:               │
               │  flow(project,                     │
               │    build_symbol_tables,           │
               │    bind(parse_all_rungs),          │
               │    bind(run_all_checks))           │
               └──────────┬───────────────────────┘
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

## Checks to Implement

```
ERRORS (block simulation):
  E001  Undefined tag reference           XIC(Moter_Run) — tag doesn't exist
  E002  Type mismatch                     TON(MyDINT,...) — DINT ≠ TIMER
  E003  Missing AOI definition            Calling My_AOI, not defined
  E004  Invalid JSR target                JSR(NoSuchRoutine,0)
  E005  Invalid UDT member access         Tag.NonExistent
  E006  Array index out of bounds         Arr[10] on Arr[10] (0-indexed)
  E007  Duplicate tag name in scope
  E008  AOI circular dependency           AOI_A → AOI_B → AOI_A
  E009  Wrong operand count               XIC() with no args
  E010  Cross-scope tag violation         Program tag used in another program

WARNINGS (allow simulation):
  W001  Unused tag declared
  W002  Unreachable rung                  AFI as first instruction
  W003  Output never driven               Used in XIC, never in OTE/OTL/OTU
  W004  Timer PRE never set               TON with PRE still 0
  W005  Shadowed tag name                 Prog tag hides ctrl tag
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

### Reuse vs Build

| Layer | Approach | What we build |
|-------|----------|---------------|
| **L5X XML parsing** | **Reuse** `jvalenzuela/l5x` | Thin adapter (`adapter.py`) mapping its models into our `SymbolTable` |
| **RLL neutral text parsing** | **Build** new Lark grammar | Full Lark grammar + transformer for ~120 instructions; use `l5x2c` as reference for branch syntax |
| **Instruction operand rules** | **Reuse** `l5x2c` tables + 1756-rm084 | Encode as data in `type_system.py`, not custom code per instruction |
| **Built-in type definitions** | **Reuse** `hutcheb/acd` struct defs | Hard-code TIMER/COUNTER/CONTROL/STRING in `builtins.py` (they never change) |
| **XSD structural validation** | **Reuse** `benmusson/l5x-schema` XSDs | Load XSD per schema revision, validate before semantic analysis |
| **Check implementations** | **Build** 15 pure functions | One file per E/W code in `checks/` |
| **Pipeline orchestration** | **Build** `flow()` composition | Wire checks together in `pipeline/analyze.py` |
| **MCP server** | **Build** FastMCP tool endpoints | `mcp_server.py` exposing `validate_l5x` etc. |

### XML Parsing — Reuse `jvalenzuela/l5x`

The `l5x` Python library is a mature, tested L5X reader/writer handling the full object model — tags, UDTs, arrays, aliases, modules, AOIs, CDATA sections. The linter only needs a thin **adapter** layer mapping its output into `SymbolTable`. Rebuilding would duplicate hundreds of lines of tested code for zero benefit.

### RLL Neutral Text — Build new Lark grammar

`alairjunior/l5x2c` has a working PLY parser for ~25 instructions but misses ~75. Rather than extend PLY, we define a **Lark** grammar covering all 100+ instructions. Lark (like ANTLR) is a parser generator — you write a grammar file, it produces a parse tree. Unlike ANTLR, Lark is Python-native with no separate code generation step, making it simpler to integrate.

```lark
?input_instruction : OPCODE "(" params ")"
params             : param ("," param)*
param              : TAG_NAME | NUMBER | "?"
```

### Why Python

Static analysis is tree-walking + symbol table lookups — not CPU-bound. Direct import of `l5x` (Python library) avoids FFI/RPC overhead. The MCP tool layer and LangGraph agent are also Python. Rust/C++/Go would add build complexity for zero performance gain in this use case.

### Testing — TDD with real L5X files

**28 test files** in `tests/data/`:
- **14 valid baselines** — real L5X files from L5Sharp's test suite covering projects, routines (RLL/ST), individual rungs, data types, AOIs
- **14 intentionally broken** — one per E001-E010 and W001-W005, each crafted to trigger exactly one diagnostic code

Workflow: implement a check → test against matching broken file → assert expected diagnostic code.

---

## Toolchain

| Tool | Purpose |
|------|---------|
| `uv` | Package management (replaces pip/poetry/virtualenv) |
| `ruff` | Code formatting + linting |
| `returns` | `Result`, `Maybe`, `flow`, `bind` for functional composition |
| `lark` | RLL neutral text parser generator |
| `jvalenzuela/l5x` | L5X XML parsing library |
| `pytest` | Test framework |

### uv Commands

```powershell
uv sync                           # Install all deps from pyproject.toml
uv add <package>                  # Add runtime dependency
uv add --dev <package>            # Add dev dependency
uv run pytest tests/ -v          # Run tests in env
uvx ruff check .                  # Lint (ephemeral)
uvx ruff format .                 # Format
```

---

## Existing OSS Referenced

| Repo | What for |
|---|---|
| `jvalenzuela/l5x` | XML parsing — adapter target |
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

## Module Structure

```
l5x_lint/
  domain/                        # Pure data types — zero dependencies
    models.py                    # Tag, DataType, Routine, ParsedRung, etc.
    diagnostics.py               # Diagnostic, Location, Severity
    errors.py                    # LintError (typed union for Result error type)
    symbol_table.py              # SymbolTable, Scope (pure query methods)
    type_system.py               # Type compatibility matrix, member resolution

  checks/                        # One pure function per E/W code
    e001_undefined_tag.py
    e002_type_mismatch.py
    e003_missing_aoi.py
    e004_invalid_jsr.py
    e005_invalid_member.py
    e006_array_oob.py
    e007_duplicate_tag.py
    e008_aoi_circular.py
    e009_operand_count.py
    e010_cross_scope.py
    w001_unused_tag.py
    w002_unreachable_rung.py
    w003_output_never_driven.py
    w004_timer_pre_zero.py
    w005_shadowed_tag.py

  pipeline/
    analyze.py                   # Compose all checks via flow()
    rung_parser.py               # Lark grammar + transformer → ParsedRung

  infrastructure/                # Impure shell — IO lives here
    adapter.py                   # Wraps l5x library → domain models
    mcp_server.py                # FastMCP server exposing MCP tools

tests/
  conftest.py
  test_data_inventory.py
  data/valid/                    # 14 baseline L5X files
  data/invalid/                  # 14 broken L5X files (one per code)
```

---

## Integration Context

```
Agent → l5x-forge:  generate_routine(...) → l5x_xml
Agent → l5x-lint:   validate_l5x(l5x_xml) → diagnostics
Agent → l5x-forge:  fix_errors(xml, diagnostics) → corrected xml
Agent → l5x-sim:    load + simulate + assert
```
