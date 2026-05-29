# IEC 61131-3 OSS Analysis — Phase 3 Feature Proposals for l5x-lint

**Research Date:** June 2026
**Submodule Roots:** `references/trust-platform/`, `references/rusty/`, `references/ironplc/`

---

## Repositories Analyzed

Three additional IEC 61131-3 open-source projects were analyzed for architectural patterns
applicable to l5x-lint. All cloned as submodules under `references/`.

| Repo | Path | Stars | Language | License | Age |
|------|------|-------|----------|---------|-----|
| **johannesPettersson80/trust-platform** | `references/trust-platform/` | ~178 | Rust | MIT/Apache-2.0 | ~4 mo |
| **PLC-lang/rusty** | `references/rusty/` | ~332 | Rust | LGPL-3.0 | ~6.5 yr |
| **ironplc/ironplc** | `references/ironplc/` | ~78 | Rust | MIT | ~4 yr |

---

## Architecture Comparison

| Feature | truST Platform | RuSTy | IronPLC | l5x-lint |
|---------|---------------|-------|---------|----------|
| Lang | Rust | Rust | Rust | Python |
| Parser | Hand-written error-tolerant | Logos + hand-written recursive descent | PEG (rust-peg) | Lark LALR(1) |
| Error codes | `DiagnosticCode` enum (E/W/I ranges) | `E001`-`E140` string codes | `P0001`-`P9999` CSV-driven enum | `LintError` union dataclass (15 variants) |
| Severity | Error/Warning/Info/Hint + overrides | Error/Warning, configurable via JSON | All errors (no warnings) | Error/Warning (fixed) |
| Warning categories | 9 toggle groups + vendor rule packs | Per-code severity JSON | N/A | None (all-on) |
| Config format | `trust-lsp.toml` | `diagnostics_*.json` | CLI `--allow-*` flags | None |
| Cross-file checks | Yes (global linkage, task hazards) | Yes (naming conflicts, duplicates) | Yes (toposort, library) | No (single-file) |
| Dialect support | Vendor profiles + IEC deviations | Case-insensitive toggle | `--dialect ed2/ed3/rusty` | None |
| Error recovery | Bounded skip + semicolon insertion | Region-based close-keyword stack | First error stops | Lark strict failure |
| Test approach | Snapshot + integration | `insta` snapshots + lit tests | Rust test + snapshot | Pytest + syrupy |

---

## Per-Repo Deep Analysis

### truST Platform (`johannesPettersson80/trust-platform`)

**Crate structure:** `trust-syntax` (parser) → `trust-hir` (type checking, diagnostics) → `trust-ide` → `trust-lsp` (tower-lsp server)

#### Diagnostic Code Architecture (`crates/trust-hir/src/diagnostics.rs`)

| Range | Category | Examples |
|-------|----------|---------|
| E001-E099 | Syntax errors | `UnexpectedToken`, `MissingToken`, `UnclosedBlock` |
| E100-E199 | Name resolution | `UndefinedVariable` (E101), `UndefinedType` (E102), `DuplicateDeclaration` (E104), `UndefinedField` (E107) |
| E200-E299 | Type errors | `TypeMismatch` (E201), `WrongArgumentCount` (E204), `MissingReturn` (E206) |
| E300-E399 | Semantic errors | `InvalidArrayIndex` (E303), `CyclicDependency` (E305), `InvalidTaskConfig` (E306) |
| W001-W099 | Warnings | `UnusedVariable`, `UnreachableCode`, `MissingElse`, `ShadowedVariable`, `HighComplexity` (W008), `NondeterministicTimeDate`, `SharedGlobalTaskHazard`, `FloatingPointEquality` (W013), `LiteralDivisionByZero` (W014) |
| I001-I099 | Info/Hints | `Simplification`, `StyleSuggestion` |

**Key type:**
```rust
pub struct Diagnostic {
    pub code: DiagnosticCode,
    pub severity: DiagnosticSeverity,
    pub range: TextRange,
    pub message: String,
    pub related: Vec<RelatedInfo>,
    pub sub_diagnostics: Vec<Diagnostic>,
}
```

**Severity overrides + warning category toggles (`crates/trust-lsp/src/config/model.rs`):**

9 boolean toggles `warn_unused`, `warn_unreachable`, `warn_missing_else`, `warn_implicit_conversion`, `warn_shadowed`, `warn_deprecated`, `warn_complexity`, `warn_nondeterminism`, `warn_numeric_hazards` + `severity_overrides: HashMap<String, DiagnosticSeverity>`.

**`rule_pack` presets:** `"iec-safety"`, `"siemens-safety"`, `"codesys-safety"`, `"beckhoff-safety"`, `"twincat-safety"`, `"mitsubishi-safety"`, `"gxworks3-safety"` — each promotes specific W-codes to errors.

**Diagnostic enhancement features:**
- `.with_related(range, message)` — points to "previously declared here" for duplicates
- `"Did you mean?"` with Levenshtein distance and adaptive thresholds
- Syntax habit hints (detects C-style `==`, `&&`, `||`, `{}` and suggests ST equivalents)
- IEC 61131-3 spec section references per diagnostic code

**Sub-checker delegation pattern:** `ExprChecker`/`StmtChecker`/`CallChecker`/`StandardChecker`/`ResolveChecker` — each as a separate view struct on the `TypeChecker`.

**Cross-file diagnostics (`crates/trust-hir/src/db/diagnostics/`):**
- `globals.rs` — duplicate global declarations, `VAR_EXTERNAL` linkage validation
- `shared_globals.rs` — cross-task shared global hazard detection (W012)
- `configuration.rs` — TASK PRIORITY validation, unknown task references (E306/E307)
- `nondeterminism.rs` — TIME/DATE type and I/O direct address detection (W010/W011)
- `unused.rs` — unused variable/parameter/POU tracking across files (W001/W002/W009)
- `complexity.rs` — cyclomatic complexity threshold (W008, default: 15)

**Parser approach:** Hand-written recursive descent with Event-based CST (rust-analyzer style). Error recovery via `is_sync_point()`, `recover_statement()`, bounded skip with bracket-depth tracking, and automatic semicolon insertion heuristics.

---

### RuSTy (`PLC-lang/rusty`)

**Module structure:** `src/validation/` with per-domain validation files.

#### Validation Module Architecture

| File | What it validates |
|------|------------------|
| `array.rs` | Bracket syntax (`[]`), element count bounds, struct-in-array initializers |
| `pou.rs` | POU structure (class restrictions, interface impl, method overrides, labels) |
| `property.rs` | Property definitions (multiple GET/SET, type conflicts, overrides) |
| `recursive.rs` | Recursive data structures (struct/FB cycles), type aliases, interface cycles — DFS |
| `statement.rs` | Assignments, type compatibility, array access, pointer deref, control flow, calls, division-by-zero, implicit downcasts |
| `types.rs` | Struct emptiness, enum validity, varargs, array bounds types |
| `variable.rs` | VLA location rules, array range validity, size overflow, constant bounds, redeclaration |
| `global.rs` | Naming conflicts (unique callables, datatypes, POUs, variables), ambiguous symbols |

Each validator exposes `visit_*` functions that take `&mut Validator` + AST node + `ValidationContext<T>`. The `Validator` owns `Vec<Diagnostic>` and uses a `Validators` derive macro.

**Error code format:** `E` + 3 digits (E001–E140).

**Diagnostic builder:**
```rust
Diagnostic::new("message")
    .with_error_code("E043")
    .with_location(location)
    .with_secondary_location(other_location)
    .with_sub_diagnostics(vec![...])
```

**Severity override via JSON:**
```json
{
    "error": ["E043", "E090"],
    "warning": ["E001"],
    "info": ["E060"],
    "ignore": ["E015"]
}
```

**Key checks applicable to l5x-lint:**

| Check | Code | Description |
|-------|------|-------------|
| Array bracket syntax | E043 | Array assignments must use `[...]`, not `(...)` |
| Too many array elements | E043 | LHS size < RHS element count |
| Too few array elements | E127 (Warning) | LHS size > RHS element count |
| Struct-in-array wrapper | E043 | Struct initializers within arrays must be parenthesized |
| Duplicate labels | E018 | Jump labels in an implementation must be unique |
| Division by zero | (statement.rs) | `DIV`/`MOD` with literal zero right operand |
| Implicit downcast | E067 | Assigning wider type to narrower type |
| Condition type | E094/E096 | IF/WHILE conditions must be BOOL or integer |
| Reserved keyword as name | E138 | Reserved keyword used as identifier |
| Recursive type cycle | (recursive.rs) | DFS for self-referencing data types |

**Parser:** logos (compile-time generated lexer) + hand-written recursive descent. Keywords are case-insensitive (`ignore(case)`). Region-based error recovery via close-keyword stack.

**Test approach:** `insta` snapshot testing with `parse_and_validate_buffered()` helper that runs the full pipeline (parse → index → annotate → validate → format) in one call.

---

### IronPLC (`ironplc/ironplc`)

**Module structure:** `compiler/parser/` → `compiler/analyzer/` (type resolution + semantic rules) → `compiler/codegen/`

#### Problem Code System

**CSV-driven enum codegen (`compiler/problems/resources/problem-codes.csv` + `compiler/problems/build.rs`):**
```
Code,Name,Message
P0001,OpenComment,End of file before comment closed
P0003,SyntaxError,Unexpected token
P4015,StdlibTypeRedefinition,User-defined type has the same name as a standard library type
```

**Code ranges:**
| Range | Category |
|-------|----------|
| P0001-P1999 | Parsing errors |
| P2000-P3999 | Type system errors |
| P4000-P5999 | Semantic analysis errors |
| P6000-P7999 | File system errors |
| P8000-P8999 | MCP tool errors |
| P9000+ | Internal/NotImplemented |

#### Dialect System (`compiler/parser/src/options.rs`)

```rust
pub enum Dialect {
    Iec61131_3Ed2,     // default — strict 2003
    Iec61131_3Ed3,     // strict 2013 (LTIME, LDATE, REF_TO, NULL)
    Rusty,             // Ed2 + REF_TO + ALL vendor extensions
    Codesys,           // Ed2 + REF_TO + Codesys extensions
}
```

15 `CompilerOptions` boolean flags gated by dialect:
- `allow_c_style_comments`, `allow_missing_semicolon`, `allow_top_level_var_global`
- `allow_ref_to`, `allow_ref_arithmetic`, `allow_ref_stack_variables`, `allow_ref_type_punning`
- `allow_int_to_bool_initializer`, `allow_sizeof`, `allow_system_uptime_global`
- `allow_cross_family_widening`, `allow_partial_access_syntax`, `allow_time_as_function_name`
- `allow_constant_type_params`, `allow_empty_var_blocks`

#### Multi-Source Format Support (`compiler/sources/src/`)

```rust
pub enum FileType {
    StructuredText,   // .st, .iec
    Xml,              // .xml (PLCopen XML)
    TwinCat,          // .TcPOU, .TcGVL, .TcDUT
    Unknown,
}
```

Detection by extension + content heuristic (starts with `<` → XML, contains `<TcPlcObject` → TwinCAT, else ST). All three formats produce the same `Library` type — a `Vec<LibraryElementKind>`.

#### Built-in Type Registry (`compiler/analyzer/src/intermediates/stdlib_function_block.rs`)

22 built-in function blocks defined via builder:
- **Bistable:** SR, RS
- **Edge detection:** R_TRIG, F_TRIG
- **Timers:** TON, TOF, TP
- **Counters:** CTU, CTU_DINT, CTU_LINT, CTU_UDINT, CTU_ULINT, CTD_*, CTUD_* (15 variants)

Each FB has typed fields (Input/Output) with offsets. Registration in `TypeEnvironmentBuilder`.

**Reserved name collision (P4015):** `is_stdlib_function_block(name)` checks against a static list with case-insensitive `Id` equality. Emits `P4015` when user defines a POU whose name shadows a built-in.

**Recoverable multi-pass analysis:** Transforms (`xform_*`) clone the Library before mutation; on failure revert and collect diagnostics, continuing to next pass. Hard failures (cyclic dependency in `xform_toposort_declarations`) stop analysis.

**Parser:** `peg` (rust-peg) inline grammar. Token-level pre-validation (`check_tokens()`) runs before parsing for C-style comments and empty var blocks. Keyword demotion strategy (`xform_demote_edition3_keywords()`) based on dialect.

---

## Phase 3 Feature Proposals

Proposals are ordered by priority and mapped to the specific source patterns that inspired them.

---

## Validation Test Cases

Every new check must be validated with both **ST** and **RLL** neutral text.
The Reference column links to the OSS repo test that inspired the check.

### W101 — Floating-Point Equality

```iecst
// ST: REAL equality comparison (triggers W101)
PROGRAM Test
VAR
    r : REAL;
    flag : BOOL;
END_VAR
    flag := (r + 0.2) = 0.3;
END_PROGRAM
```

```iecst
// ST: LREAL inequality comparison (triggers W101)
PROGRAM Test
VAR
    lr : LREAL;
    flag : BOOL;
END_VAR
    flag := lr <> 3.14;
END_PROGRAM
```

```iecst
// ST: DINT comparison — NO diagnostic (int comparison is safe)
PROGRAM Test
VAR
    x : DINT;
    y : DINT;
    flag : BOOL;
END_VAR
    flag := x = y;
END_PROGRAM
```

```iecst
// RLL: CPT with REAL comparison (triggers W101)
CPT(Flag, Motor_Speed = 100.5);
```

```iecst
// RLL: GRT/LES on REAL (triggers W101)
GRT(Motor_Speed, 99.9)OTE(HighSpeed);
```

**Reference:** truST `crates/trust-hir/tests/semantic_type_checking/basics_and_warnings.rs` lines 457-469
**File to create:** `tests/data/invalid/W101_float_equality.L5X`

### W102 — Division by Literal Zero

```iecst
// ST: Division by literal zero (triggers W102)
PROGRAM Test
VAR
    x : DINT;
    result : DINT;
END_VAR
    result := x / 0;
END_PROGRAM
```

```iecst
// ST: MOD with literal zero (triggers W102)
PROGRAM Test
VAR
    x : DINT;
    result : DINT;
END_VAR
    result := x MOD 0;
END_PROGRAM
```

```iecst
// ST: Parenthesized zero (triggers W102)
PROGRAM Test
VAR
    x : DINT;
    result : DINT;
END_VAR
    result := x / (0);
END_PROGRAM
```

```iecst
// ST: Variable divisor — NO diagnostic (runtime variable can't be statically proven)
PROGRAM Test
VAR
    x : DINT := 5;
    y : DINT := 0;
    result : DINT;
END_VAR
    result := x / y;  // y is variable, not literal zero
END_PROGRAM
```

```iecst
// RLL: CPT with division by zero (triggers W102)
CPT(Dest, A / 0);
```

**Reference:** RuSTy `src/validation/tests/statement_validation_tests.rs` lines 2783-2942
**File to create:** `tests/data/invalid/W102_div_by_zero.L5X`

### W103 — Cyclomatic Complexity

```iecst
// ST: 15+ branching points (triggers W103 at threshold 15)
PROGRAM Test
VAR
    x : DINT;
END_VAR
    IF x = 1 THEN x := x + 1; END_IF;
    IF x = 2 THEN x := x + 1; END_IF;
    IF x = 3 THEN x := x + 1; END_IF;
    IF x = 4 THEN x := x + 1; END_IF;
    IF x = 5 THEN x := x + 1; END_IF;
    IF x = 6 THEN x := x + 1; END_IF;
    IF x = 7 THEN x := x + 1; END_IF;
    IF x = 8 THEN x := x + 1; END_IF;
    IF x = 9 THEN x := x + 1; END_IF;
    IF x = 10 THEN x := x + 1; END_IF;
    IF x = 11 THEN x := x + 1; END_IF;
    IF x = 12 THEN x := x + 1; END_IF;
    IF x = 13 THEN x := x + 1; END_IF;
    IF x = 14 THEN x := x + 1; END_IF;
    IF x = 15 THEN x := x + 1; END_IF;
    IF x = 16 THEN x := x + 1; END_IF;
END_PROGRAM
```

```iecst
// RLL: Rung with 15+ branches (triggers W103)
XIC(A)OTE(Z);
XIO(B)OTE(Z);
XIC(C)OTE(Z);
XIO(D)OTE(Z);
XIC(E)OTE(Z);
XIO(F)OTE(Z);
XIC(G)OTE(Z);
XIO(H)OTE(Z);
XIC(I)OTE(Z);
XIO(J)OTE(Z);
XIC(K)OTE(Z);
XIO(L)OTE(Z);
XIC(M)OTE(Z);
XIO(N)OTE(Z);
XIC(O)OTE(Z);
XIO(P)OTE(Z);
```

**Reference:** truST `crates/trust-hir/tests/semantic_type_checking/basics_and_warnings.rs` lines 281-297
**File to create:** `tests/data/invalid/W103_complexity.L5X`

### E011 — Reserved Name Collision

```iecst
// ST: AOI named TON shadows built-in (triggers E011)
FUNCTION_BLOCK TON
VAR_INPUT
    value : INT;
END_VAR
END_FUNCTION_BLOCK
```

```iecst
// ST: AOI named CTU shadows built-in (triggers E011)
FUNCTION_BLOCK CTU
VAR_INPUT
    value : INT;
END_VAR
END_FUNCTION_BLOCK
```

```iecst
// ST: Custom name — NO diagnostic
FUNCTION_BLOCK MY_CUSTOM_FB
VAR_INPUT
    value : INT;
END_VAR
END_FUNCTION_BLOCK
```

```iecst
// RLL: Custom AOI call with built-in name (triggers E011)
My_TON(MyTimer, ?, ?);
```

**Implementation note:** The reserved name list must match `_BUILTIN_OPCODES` in `checks/opcodes.py` plus Rockwell's built-in type names (TON, TOF, CTU, CTD, etc.).
**Reference:** IronPLC `compiler/analyzer/src/rule_stdlib_type_redefinition.rs` lines 78-132
**File to create:** `tests/data/invalid/E011_reserved_name.L5X`

### E012 — Array Initializer Element Count Mismatch

```iecst
// ST: Array type with 5 elements, initialized with 3 (triggers E012)
TYPE MyArray : ARRAY[1..5] OF INT := [1, 2, 3];
END_TYPE
```

```iecst
// ST: Array variable with 10 elements, initialized with 3 (triggers E012)
PROGRAM Test
VAR
    arr : ARRAY[1..10] OF INT := [1, 2, 3];
END_VAR
END_PROGRAM
```

```iecst
// ST: Correct count — NO diagnostic
PROGRAM Test
VAR
    arr : ARRAY[1..3] OF INT := [10, 20, 30];
END_VAR
END_PROGRAM
```

**Reference:** RuSTy `src/validation/tests/array_validation_test.rs` lines 820-848, `tests/lit/single/init/array_partial_init_warning_type_and_var.st`
**File to create:** `tests/data/invalid/E012_array_init_count.L5X`

### W104 — Non-BOOL Condition

```iecst
// ST: IF with DINT condition (triggers W104)
PROGRAM Test
VAR
    x : DINT;
    y : DINT;
END_VAR
    IF y THEN
        x := 1;
    END_IF
END_PROGRAM
```

```iecst
// ST: WHILE with DINT condition (triggers W104)
PROGRAM Test
VAR
    x : DINT;
    y : DINT;
END_VAR
    WHILE y DO
        y := y - 1;
    END_WHILE
END_PROGRAM
```

```iecst
// ST: IF with BOOL condition — NO diagnostic
PROGRAM Test
VAR
    x : DINT;
    ok : BOOL;
END_VAR
    IF ok THEN
        x := 1;
    END_IF
END_PROGRAM
```

```iecst
// ST: IF with comparison expression — NO diagnostic (result is BOOL)
PROGRAM Test
VAR
    x : DINT;
    y : DINT;
END_VAR
    IF x = y THEN
        x := 1;
    END_IF
END_PROGRAM
```

```iecst
// RLL: XIC/XIO always use BOOL, so W104 is ST-only
```

**Reference:** RuSTy `src/validation/tests/statement_validation_tests.rs` lines 2109-2186
**File to create:** `tests/data/invalid/W104_non_bool_condition.L5X`

### W105 — Implicit Downcast

```iecst
// ST: Assign LINT to DINT (triggers W105)
PROGRAM Test
VAR
    narrow : DINT;
    wide : LINT;
END_VAR
    narrow := wide;
END_PROGRAM
```

```iecst
// ST: Assign REAL to DINT (triggers W105)
PROGRAM Test
VAR
    int_val : DINT;
    real_val : REAL;
END_VAR
    int_val := real_val;
END_PROGRAM
```

```iecst
// ST: Assign DINT to LINT — NO diagnostic (widening is safe)
PROGRAM Test
VAR
    narrow : DINT;
    wide : LINT;
END_VAR
    wide := narrow;
END_PROGRAM
```

```iecst
// ST: Assign DINT to DINT — NO diagnostic (same type)
PROGRAM Test
VAR
    a : DINT;
    b : DINT;
END_VAR
    a := b;
END_PROGRAM
```

```iecst
// RLL: MOV from REAL to DINT (triggers W105)
MOV(RealVal, DintDest);
```

**Reference:** RuSTy `src/validation/tests/variable_validation_tests.rs` lines 1647-1695, `statement_validation_tests.rs` lines 1542-1720
**File to create:** `tests/data/invalid/W105_implicit_downcast.L5X`

### W106 — Unused POU

```iecst
// ST: Unreferenced function block (triggers W106)
FUNCTION_BLOCK UnusedFb
VAR_INPUT
    x : DINT;
END_VAR
END_FUNCTION_BLOCK

PROGRAM Main
VAR
    result : DINT;
END_VAR
    result := 42;
END_PROGRAM
// UnusedFb is never instantiated
```

```iecst
// RLL: Unreferenced routine (triggers W106 — routine in L5X that's never JSR'd)
```

**Reference:** truST `crates/trust-hir/tests/semantic_type_checking/basics_and_warnings.rs` lines 301-309
**File to create:** `tests/data/invalid/W106_unused_pou.L5X`

### W107 — Missing ELSE

```iecst
// ST: IF without ELSE (triggers W107)
PROGRAM Test
VAR
    x : DINT;
END_VAR
    IF x > 0 THEN
        x := 1;
    END_IF
END_PROGRAM
```

```iecst
// ST: IF with ELSE — NO diagnostic
PROGRAM Test
VAR
    x : DINT;
END_VAR
    IF x > 0 THEN
        x := 1;
    ELSE
        x := -1;
    END_IF
END_PROGRAM
```

```iecst
// ST: CASE without ELSE (triggers W107)
PROGRAM Test
VAR
    x : DINT;
END_VAR
    CASE x OF
        1: x := 10;
        2: x := 20;
    END_CASE
END_PROGRAM
```

```iecst
// ST: CASE with ELSE — NO diagnostic
PROGRAM Test
VAR
    x : DINT;
END_VAR
    CASE x OF
        1: x := 10;
        2: x := 20;
    ELSE
        x := 0;
    END_CASE
END_PROGRAM
```

**Reference:** truST `crates/trust-hir/tests/semantic_type_checking/control_flow_and_calls.rs` lines 191-231
**File to create:** `tests/data/invalid/W107_missing_else.L5X`

---

### Implementation Steps Per Check

Each new check follows this recipe:

| Step | What | Test Pattern |
|------|------|-------------|
| 1 | Create `errors.py` variant | Add dataclass with `code`, `severity`, `message_template`, `description` |
| 2 | Add to `LintError` union type | Append `\|` to the union |
| 3 | Create check function | `@register` def in `checks/wNNN_name.py` |
| 4 | Create invalid L5X test file | `tests/data/invalid/WNNN_name.L5X` with CDATA triggering the check |
| 5 | Create valid L5X test file (no-fire) | `tests/data/valid/` — same structure with no trigger |
| 6 | Create unit test | `tests/checks/test_wNNN_name.py` — test invalid triggers, valid no-fire |
| 7 | Update integration test | Add to parametrized test in `tests/test_integration.py` |
| 8 | Update opcodes/builtins if needed | For E011, extend `_BUILTIN_OPCODES` in `checks/opcodes.py` |

---

### P3.1 Diagnostic Config System (High Priority)

**Source patterns:** truST `DiagnosticSettings` + RuSTy `DiagnosticsConfiguration` + IronPLC `CompilerOptions`

l5x-lint currently has hardcoded severities (E=error, W=warning). Users and agents
need configurable severity per project.

```python
@dataclass
class LintConfig:
    """Per-workspace lint configuration. Loaded from l5x-lint.toml in project root."""
    # --- Warning category toggles ---
    warn_unused: bool = True            # W001
    warn_unreachable: bool = True       # W002
    warn_output_never_driven: bool = True  # W003
    warn_timer_pre: bool = True         # W004
    warn_shadowed: bool = True          # W005
    warn_numeric_hazards: bool = False  # W101, W102 (new)
    warn_complexity: bool = False       # W103 (new)

    # --- Per-code severity overrides ---
    severity_overrides: dict[str, str] = field(default_factory=dict)
    #   e.g., {"W001": "error", "E001": "warning"}

    # --- Rule pack presets ---
    rule_pack: str | None = None
    #   "safety"      → promote W004, W005 to error
    #   "rockwell"    → Rockwell/Studio 5000 defaults
    #   "iec-61131-3" → strict IEC standard

    # --- Vendor dialect ---
    dialect: str = "rockwell"
    #   "rockwell"    → lowercase keywords, positional args, JSR
    #   "iec-61131-3" → uppercase keywords, named args
    #   "codesys"     → CodeSys dialect
    #   "twincat"     → Beckhoff TwinCAT dialect

    def apply_rule_pack(self) -> None:
        match self.rule_pack:
            case "safety":
                self.severity_overrides.update({"W004": "error", "W005": "error"})
                self.warn_numeric_hazards = True
                self.warn_unreachable = True
            case "rockwell":
                self.warn_numeric_hazards = False
            case "iec-61131-3":
                self.warn_output_never_driven = True
                self.warn_complexity = True

    @classmethod
    def from_toml(cls, path: Path) -> "LintConfig":
        """Load from l5x-lint.toml. Missing keys use defaults."""
        ...

    def diagnostic_allowed(self, code: str, severity: str) -> bool:
        """Filter pipeline: map code to category toggle."""
        match code:
            case "W001": return self.warn_unused
            case "W002": return self.warn_unreachable
            case "W003": return self.warn_output_never_driven
            case "W004": return self.warn_timer_pre
            case "W005": return self.warn_shadowed
            case "W101" | "W102": return self.warn_numeric_hazards
            case "W103": return self.warn_complexity
            case _: return True  # errors always shown

    def resolve_severity(self, code: str, default_severity: str) -> str:
        return self.severity_overrides.get(code, default_severity)
```

**Config file format (`l5x-lint.toml`):**

```toml
[diagnostics]
warn_unused = true
warn_unreachable = true
warn_numeric_hazards = true
rule_pack = "safety"

[diagnostics.severity_overrides]
W001 = "error"
E001 = "warning"

[dialect]
name = "rockwell"
```

**Pipeline integration:**

```python
# In pipeline/analyze.py
def analyze(project: L5XProject, config: LintConfig | None = None) -> AnalysisResult:
    config = config or LintConfig()
    diagnostics = flow(
        project,
        build_symbol_tables,
        bind(parse_all_routine_content),
        bind(lambda p: run_all_checks(p, config)),
    )
    # Apply filter pipeline
    diagnostics = [
        d for d in diagnostics
        if config.diagnostic_allowed(d.code, d.severity)
    ]
    # Apply severity overrides
    for d in diagnostics:
        d.severity = config.resolve_severity(d.code, d.severity)
    return AnalysisResult.from_diagnostics(diagnostics)
```

---

### P3.2 New Checks from OSS Analysis

**Source patterns:** truST W008-W014, RuSTy E043/E127/E133, IronPLC P4015

```python
# errors.py — New LintError variants

# Block-level numeric hazard warnings
@dataclass
class W101(LintErrorBase):
    code: ClassVar[str] = "W101"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "Floating-point equality comparison involves '{name}' (REAL/LREAL)"
    description: ClassVar[str] = "Floating-point equality/inequality is hazardous due to precision. Consider using an epsilon comparison."
    name: str

@dataclass
class W102(LintErrorBase):
    code: ClassVar[str] = "W102"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "Division or modulo by literal zero in expression"
    description: ClassVar[str] = "Dividing or taking modulo by zero causes a runtime fault."
    routine: str; line: int

# Cyclomatic complexity warning — truST W008 analog
@dataclass
class W103(LintErrorBase):
    code: ClassVar[str] = "W103"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "Routine '{routine}' has cyclomatic complexity {complexity} (threshold: {threshold})"
    description: ClassVar[str] = "High complexity makes logic hard to verify. Consider splitting into sub-routines."
    routine: str; complexity: int; threshold: int = 15

# Reserved name collision — IronPLC P4015 analog
@dataclass
class E011(LintErrorBase):
    code: ClassVar[str] = "E011"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "User-defined tag/AOI '{name}' shadows built-in instruction name"
    description: ClassVar[str] = "Tag or AOI name collides with a built-in Logix instruction (TON, CTU, MOV, etc.)."
    name: str

# Array initializer element count mismatch — RuSTy E043/E127 analog
@dataclass
class E012(LintErrorBase):
    code: ClassVar[str] = "E012"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Array '{name}': initializer has {actual} elements but dimension expects {expected}"
    description: ClassVar[str] = "Array tag initializer element count does not match declared dimension."
    name: str; expected: int; actual: int
    severity: ClassVar[str] = "error"

# Condition type check — RuSTy E094/E096 analog
@dataclass
class W104(LintErrorBase):
    code: ClassVar[str] = "W104"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "IF/WHILE condition uses non-BOOL type '{actual}' in routine '{routine}'"
    description: ClassVar[str] = "IF and WHILE conditions should evaluate to BOOL. Non-BOOL conditions are always true if non-zero."
    routine: str; actual: str

# Implicit downcast — RuSTy E067 analog
@dataclass
class W105(LintErrorBase):
    code: ClassVar[str] = "W105"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "Implicit downcast from '{source_type}' to '{target_type}' in assignment to '{name}'"
    description: ClassVar[str] = "Assigning a wider type to a narrower type may truncate. Logix allows this implicitly."
    name: str; source_type: str; target_type: str

# Unused POU (program/routine) — truST W009 analog
@dataclass
class W106(LintErrorBase):
    code: ClassVar[str] = "W106"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "Program/routine '{name}' is never referenced"
    description: ClassVar[str] = "Unreferenced program or routine. MainRoutine is always considered referenced."
    name: str

# Missing ELSE on conditional — truST W004 analog
@dataclass
class W107(LintErrorBase):
    code: ClassVar[str] = "W107"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "IF statement in routine '{routine}' has no ELSE clause"
    description: ClassVar[str] = "IF without ELSE may leave outputs in unknown state. Consider adding ELSE."
    routine: str; line: int
```

**Updated LintError union:**

```python
LintError = E001 | E002 | E003 | E004 | E005 | E006 | E007 | E008 | E009 | E010 | E011 | E012 | \
            W001 | W002 | W003 | W004 | W005 | W101 | W102 | W103 | W104 | W105 | W106 | W107
```

**Full check table (updated):**

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
  E011  Reserved name collision           AOI named "TON" shadows built-in            🔷 NEW
  E012  Array init element count          Arr[5] initialized with 3 values             🔷 NEW

WARNINGS (allow simulation):
  W001  Unused tag declared                                                           ✅
  W002  Unreachable rung                  AFI as first instruction                    ✅
  W003  Output never driven               Used in XIC, never in OTE/OTL/OTU          ✅
  W004  Timer PRE never set               TON with PRE still 0                       ✅
  W005  Shadowed tag name                 Prog tag hides ctrl tag                    ✅
  W101  Floating-point equality           REAL = REAL comparison                       🔷 NEW
  W102  Division by literal zero          DIV(x, 0) = y                                🔷 NEW
  W103  Cyclomatic complexity             Routine with 20 branches                     🔷 NEW
  W104  Non-BOOL condition                IF MyDINT instead of IF MyBOOL              🔷 NEW
  W105  Implicit downcast                 DINT → SINT truncation                      🔷 NEW
  W106  Unused POU                        Unreferenced program/routine                🔷 NEW
  W107  Missing ELSE                      IF without ELSE clause                      🔷 NEW
```

---

### P3.3 Diagnostic Enhancement (Related Info + Hints)

**Source pattern:** truST `Diagnostic::with_related()` + "Did you mean?" + syntax habit hints

```python
@dataclass
class RelatedInfo:
    location: Location
    message: str

@dataclass
class Diagnostic:
    code: str
    severity: str
    location: Location
    message: str
    hint: str | None = None
    fix_suggestion: str | None = None
    related: list[RelatedInfo] = field(default_factory=list)   # 🔷 NEW
    sub_diagnostics: list[Diagnostic] = field(default_factory=list)  # 🔷 NEW
    iec_reference: str | None = None                            # 🔷 NEW

def suggest_did_you_mean(name: str, known_names: list[str]) -> str | None:
    """Levenshtein-based suggestion with adaptive threshold."""
    candidates = [
        (n, levenshtein(name.lower(), n.lower()))
        for n in known_names
    ]
    candidates.sort(key=lambda x: x[1])
    best_dist = candidates[0][1] if candidates else 99
    if best_dist <= 2:
        return f"Did you mean '{candidates[0][0]}'?"
    if best_dist <= 4:
        matches = [n for n, d in candidates if d == best_dist]
        return f"Did you mean '{matches[0]}'?"
    return None

def syntax_habit_hints(message: str) -> str | None:
    """Detect C-style syntax habits in ST code and suggest IEC equivalents."""
    hints = {
        "==": "Use '=' for equality comparison in ST (not '==')",
        "!=": "Use '<>' for inequality in ST (not '!=')",
        "&&": "Use 'AND' for logical AND in ST (not '&&')",
        "||": "Use 'OR' for logical OR in ST (not '||')",
        "{": "ST uses '(* *)' or '//' for comments, not '{ }'",
    }
    for pattern, hint in hints.items():
        if pattern in message:
            return hint
    return None
```

**Usage in checks:**

```python
def e007_duplicate_tag(project, symbols, loc) -> list[Diagnostic]:
    diags = []
    seen: dict[str, Tag] = {}
    for tag in project.all_tags():
        prev = seen.get(tag.name)
        if prev:
            diags.append(Diagnostic(
                "E007", "error",
                Location(program=tag.scope, ...),
                f"Duplicate tag '{tag.name}'",
                related=[RelatedInfo(
                    Location(program=prev.scope, ...),
                    "Previously declared here"
                )],
            ))
        seen[tag.name] = tag
    return diags
```

---

### P3.4 Sub-Checker Delegation Architecture (Medium Priority)

**Source pattern:** truST `ExprChecker`/`StmtChecker`/`CallChecker` delegation

As the check surface grows beyond 20+ checks, partition the monolithic `run_all_checks`
into domain-specific sub-checkers:

```python
# checks/checker.py
class ExprChecker:
    """Expression-level checks: type compatibility, operands, literals."""
    def check_binary_op(self, expr: StBinaryOp, symbols: SymbolTable) -> list[Diagnostic]: ...
    def check_call(self, expr: StCall, symbols: SymbolTable) -> list[Diagnostic]: ...
    def check_literal(self, expr: StLiteral) -> list[Diagnostic]: ...

class StmtChecker:
    """Statement-level checks: assignments, control flow, jumps."""
    def check_assignment(self, stmt: StAssignment, symbols: SymbolTable) -> list[Diagnostic]: ...
    def check_if(self, stmt: StIf) -> list[Diagnostic]: ...
    def check_for(self, stmt: StFor) -> list[Diagnostic]: ...

class DeclChecker:
    """Declaration-level checks: symbols, types, scopes."""
    def check_tag(self, tag: Tag, symbols: SymbolTable) -> list[Diagnostic]: ...
    def check_data_type(self, dt: DataType) -> list[Diagnostic]: ...
    def check_aoi(self, aoi: AOI, symbols: SymbolTable) -> list[Diagnostic]: ...
```

---

### P3.5 Dialect System (Medium Priority)

**Source pattern:** IronPLC `--dialect` + `CompilerOptions`

```python
@dataclass
class DialectConfig:
    name: str
    allow_keywords_case_insensitive: bool = True
    allow_positional_args: bool = True      # Rockwell style
    allow_jsr: bool = True                   # Rockwell-specific JSR
    allow_wildcard_operands: bool = True     # ? for TON/TOF PRE/ACC
    allow_type_punning: bool = True          # implicit DINT := BOOL
    allow_c_style_comments: bool = True      # // line comments
    allow_cross_family_widening: bool = True # Rockwell: any numeric → any numeric

DIALECT_PRESETS: dict[str, DialectConfig] = {
    "rockwell": DialectConfig(
        name="rockwell",
        allow_keywords_case_insensitive=True,
        allow_positional_args=True,
        allow_jsr=True,
        allow_wildcard_operands=True,
        allow_type_punning=True,
        allow_c_style_comments=True,
    ),
    "iec-61131-3": DialectConfig(
        name="iec-61131-3",
        allow_keywords_case_insensitive=False,
        allow_positional_args=False,
        allow_jsr=False,
        allow_wildcard_operands=False,
        allow_type_punning=False,
        allow_c_style_comments=False,
    ),
    "codesys": DialectConfig(
        name="codesys",
        allow_keywords_case_insensitive=False,
        allow_positional_args=True,
        allow_jsr=False,
        allow_wildcard_operands=True,
        allow_type_punning=True,
        allow_c_style_comments=True,
    ),
}
```

---

## Updated Module Structure (Phase 3 Additions)

```
l5x_lint/
  domain/                        # ✅ DONE
    ...
    diagnostics.py               #     + RelatedInfo, sub_diagnostics, iec_reference
    errors.py                    #     + E011, E012, W101-W107 (12 new variants)

  checks/                        # ✅ DONE (15 checks) + 🔷 NEW (6 checks)
    ...
    e011_reserved_name.py        #     P4015 analog: user name vs built-in instruction
    e012_array_init_count.py     #     Array initializer element count mismatch
    w101_float_equality.py       #     REAL = REAL comparison warning
    w102_div_by_zero.py          #     Division/modulo by literal zero
    w103_complexity.py           #     Cyclomatic complexity threshold
    w104_non_bool_condition.py   #     IF/WHILE condition type check
    w105_implicit_downcast.py    #     Wide-to-narrow assignment truncation
    w106_unused_pou.py           #     Unreferenced program/routine
    w107_missing_else.py         #     IF without ELSE clause

  pipeline/
    ...
    config.py                    # 🔷 NEW — LintConfig, DialectConfig, severity overrides
    filter.py                    # 🔷 NEW — Diagnostic filter + override pipeline

  infrastructure/
    ...

  presentation/
    cli.py                       #     + --diagnostic-config, --dialect flags
    mcp_server.py                #     + config tool for agents
```

---

## Existing OSS Referenced (Updated)

| Repo | What for |
|---|---|
| `jvalenzuela/l5x` | Tag value parsing (Decorated/L5K data) |
| `alairjunior/l5x2c` | RLL grammar reference, operand type tables |
| `tnunnink/L5Sharp` | 46 test L5X files, C# object model reference |
| `hutcheb/acd` | Full L5X element model, built-in struct definitions |
| `benmusson/l5x-schema` | XSD schemas for structural validation |
| Rockwell 1756-rm084 | Ground truth for instruction semantics |
| **`johannesPettersson80/trust-platform`** | **Diagnostic config + severity overrides + rule packs + related info + "Did you mean?" + sub-checker delegation + warning category toggles** |
| **`PLC-lang/rusty`** | **Array validation patterns + condition type checking + reserved keyword validation + diagnostic severity config JSON + region-based error recovery** |
| **`ironplc/ironplc`** | **Dialect system + multi-source format dispatch + built-in FB registry + reserved name collision (P4015) + problem code CSV registry + token-level pre-validation** |

---

## Phase 3 Implementation Priority

| Feature | Effort | Impact | Source |
|---------|--------|--------|--------|
| **Diagnostic config (P3.1)** | Medium | High — enables agent tuning, CI gating by severity | truST + RuSTy |
| **Numeric hazard checks (W101/W102)** | Small | Medium — catches runtime faults statically | truST |
| **Complexity warning (W103)** | Small | Medium — guides routine factoring | truST |
| **Reserved name collision (E011)** | Small | High — prevents subtle shadowing bugs | IronPLC |
| **Implicit downcast (W105)** | Medium | Medium — catches truncation bugs | RuSTy |
| **Missing ELSE (W107)** | Small | Low-medium — style/defensive | truST |
| **Condition type check (W104)** | Small | Low — edge case in Logix | RuSTy |
| **Array init count (E012)** | Medium | Low-medium — array init is rare in Logix | RuSTy |
| **Unused POU (W106)** | Medium | Medium — useful for dead code | truST |
| **Related info + hints (P3.3)** | Medium | High — better agent diagnostics | truST |
| **Dialect system (P3.5)** | Large | High — enables non-Rockwell use | IronPLC |
| **Sub-checker delegation (P3.4)** | Large | Medium — pays off at 25+ checks | truST |
