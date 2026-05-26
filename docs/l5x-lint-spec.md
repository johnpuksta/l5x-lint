# l5x-lint — Semantic Analyzer for L5X PLC Programs

**Phase 2 of the L5X Autonomous PLC Agent Toolchain**

---

## Purpose

Semantic analyzer — the "dotnet build" / compiler equivalent.
Consumes an L5X AST and produces structured, agent-readable diagnostics.
No execution — pure static analysis.

---

## Architecture

```python
class SemanticAnalyzer:
    def __init__(self, project: L5XProject):
        self.ctrl_scope  = SymbolTable(project.tags, project.data_types)
        self.aoi_table   = AOITable(project.add_on_instructions)
        self.type_system = TypeSystem(project.data_types)

    def analyze(self) -> AnalysisResult:
        errors, warnings = [], []
        for program in self.project.programs:
            prog_scope = SymbolTable(program.tags, parent=self.ctrl_scope)
            for routine in program.routines:
                checker = self._get_checker(routine.type)
                checker.check(routine, prog_scope, errors, warnings)
        return AnalysisResult(errors=errors, warnings=warnings)
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

### XML Parsing — Use `jvalenzuela/l5x` (don't rebuild)

The `l5x` Python library is a mature, tested L5X reader/writer handling the full object model — tags, UDTs, arrays, aliases, modules, AOIs, CDATA sections. The linter only needs a thin **adapter** layer mapping its output into `SymbolTable`. Rebuilding would duplicate hundreds of lines of tested code for zero benefit.

### RLL Neutral Text — Lark grammar (partial rebuild)

`alairjunior/l5x2c` has a working PLY parser for ~25 instructions but misses ~75. Rather than extend PLY, we define a **[Lark](https://github.com/lark-parser/lark)** grammar covering all 100+ instructions. Lark is a Python parsing toolkit (similar to ANTLR but native Python, no code generation step). The grammar is declarative and produces better error messages — critical for linter diagnostics.

```
Example Lark rule:
?input_instruction : OPCODE "(" params ")"
params             : param ("," param)*
param              : TAG_NAME | NUMBER | "?"
```

Lark vs ANTLR: Both are parser generators that take a grammar file and produce a parse tree. ANTLR generates standalone code in Java/JS/Python/etc. and is heavier (separate build step). Lark runs directly from the grammar at runtime (or optionally generates a standalone parser), is Python-native, and simpler to integrate for a pure-Python project. ANTLR would be overkill here.

### Why Python

Static analysis is tree-walking + symbol table lookups — not CPU-bound. Direct import of `l5x` (Python library) avoids FFI/RPC overhead. The MCP tool layer and LangGraph agent are also Python. Rust/C++/Go would add build complexity for zero performance gain in this use case.

### Testing — TDD with real L5X files

**28 test files** in `tests/data/`:
- **14 valid baselines** — real L5X files from L5Sharp's test suite covering projects, routines (RLL/ST), individual rungs, data types, AOIs
- **14 intentionally broken** — one per E001-E010 and W001-W005, each crafted to trigger exactly one diagnostic code

Workflow: implement a check → test against matching broken file → assert expected diagnostic code.

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
  adapter.py          # l5x library → SymbolTable
  rll_grammar.py      # Lark grammar file
  rll_parser.py       # Lark transformer → ParsedRung AST
  builtins.py         # Built-in type registry (TIMER, COUNTER...)
  symbol_table.py     # Scope-aware tag/type resolution
  type_checker.py     # Type compatibility checks
  analyzer.py         # SemanticAnalyzer orchestrator
  checks.py           # E001-E010, W001-W005 implementations
  diagnostics.py      # Output models
  mcp_server.py       # FastMCP server
tests/
  conftest.py
  test_data_inventory.py
  data/valid/         # 14 baseline L5X files
  data/invalid/       # 14 broken L5X files (one per code)
```

---

## Integration Context

```
Agent → l5x-forge:  generate_routine(...) → l5x_xml
Agent → l5x-lint:   validate_l5x(l5x_xml) → diagnostics
Agent → l5x-forge:  fix_errors(xml, diagnostics) → corrected xml
Agent → l5x-sim:    load + simulate + assert
```
