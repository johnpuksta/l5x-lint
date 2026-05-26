# l5x-lint — Semantic Analyzer for L5X PLC Programs

**Phase 2 of the L5X Autonomous PLC Agent Toolchain**

---

## Purpose

Semantic analyzer — the "dotnet build" / compiler equivalent.
Consumes l5x-core's AST and produces structured, agent-readable diagnostics.
No execution — pure static analysis.

### Tech Stack: Python 3.12+

**Why Python:** Static analysis is tree-walking + symbol table lookups.
Python is fast enough, and staying in the same language as l5x-core
means direct import — no RPC overhead for the hot validation loop.

---

## Architecture

```python
class SemanticAnalyzer:
    def __init__(self, project: L5XProject):
        # Build symbol tables on construction
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

## Checks to Implement (Priority Order)

```
ERRORS (block simulation):
  E001  Undefined tag reference           XIC(Moter_Run) — tag doesn't exist
  E002  Type mismatch                     TON(MyDINT,...) — DINT ≠ TIMER
  E003  Missing AOI definition            Calling My_AOI, not defined
  E004  Invalid JSR target                JSR(NoSuchRoutine,0)
  E005  Invalid UDT member access         Tag.NonExistent
  E006  Array index out of bounds         Arr[10] on Arr[10] (0-indexed)
  E007  Duplicate tag name in scope       Same name, same scope
  E008  AOI circular dependency           AOI_A → AOI_B → AOI_A
  E009  Wrong operand count               XIC() with no args
  E010  Cross-scope tag violation         Program tag used in another program

WARNINGS (allow simulation):
  W001  Unused tag declared               Tag defined, never referenced
  W002  Unreachable rung                  AFI as first instruction always false
  W003  Output never driven              Tag used in XIC, never in OTE/OTL/OTU
  W004  Timer PRE never set              TON with PRE still 0
  W005  Shadowed tag name               Prog-scope tag shadows ctrl-scope same name
```

---

## Structured Output for Agent Consumption

```json
{
  "passed": false,
  "error_count": 2,
  "warning_count": 1,
  "diagnostics": [
    {
      "code": "E001",
      "severity": "error",
      "location": { "program": "MainProgram", "routine": "MainRoutine", "rung": 4 },
      "message": "Undefined tag reference 'Moter_Run'",
      "hint": "Did you mean 'Motor_Run'? (edit distance: 1)",
      "fix_suggestion": "Change 'Moter_Run' to 'Motor_Run', or declare tag 'Moter_Run' as BOOL"
    }
  ]
}
```

The `fix_suggestion` field is critical — it lets the agent fix without
another expensive LLM call for simple typos and type errors.

---

## Existing OSS to Leverage

| Repo | What to take |
|---|---|
| `alairjunior/l5x2c` | Instruction operand type tables (what type each operand expects) |
| `lark` (existing L5X grammar repo) | Starting point for RLL parser used in type-checking pass |
| Rockwell General Instructions Ref Manual (1756-rm084) | Ground truth for every instruction's operand types |

---

## MCP Tools Exposed

```
validate_l5x(l5x_xml: str) → AnalysisResult
check_tag_references(l5x_xml: str) → list[TagRefError]
get_cross_references(l5x_xml: str, tag_name: str) → CrossRefResult
suggest_fixes(diagnostic: Diagnostic) → list[FixSuggestion]
```

---

## Integration Context

l5x-lint sits between l5x-core (AST provider) and the agent orchestrator
in the toolchain data flow:

```
Agent → l5x-forge:  generate_routine("conveyor with E-stop")
                     returns: l5x_xml_v1

Agent → l5x-lint:   validate_l5x(l5x_xml_v1)
                     returns: { errors: [E001: 'Moter_Run' undefined] }

Agent → l5x-forge:  fix_errors(l5x_xml_v1, diagnostics)
                     returns: l5x_xml_v2  (typo fixed)
```

## Build Order Context

Part of **Phase 2 — RLL + ST Simulation (6–8 weeks)**.
l5x-core must be built first (Phase 1) since l5x-lint depends on its AST.

**Success criteria for Phase 2:** Agent autonomously debugs a broken motor
routine using trace feedback, fixes the logic, re-runs, passes all assertions.
