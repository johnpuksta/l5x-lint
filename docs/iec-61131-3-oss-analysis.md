# IEC 61131-3 OSS Analysis — Implementation Plan for l5x-lint

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

## Implementation Plan

This is the single plan. Everything after this section is reference material
(code examples, architecture definitions, OSS code indexes).

The plan has 3 rounds executed in order:

| Round | What | Outcome |
|-------|------|---------|
| 1 | Prefix scheme + migration | Define `{E\|W}{C\|R\|S\|F}{NNN}` scheme, rename 15 existing codes, restructure into `cross/`/`rll/`/`st/` |
| 2 | Type resolver + all new checks (~34) | Build `resolve_type()` first, then all checks from the registry in one pass (EC011, WS101, ER013, etc.) |
| 3 | Plumbing features | Config system, related info, sub-checker delegation, dialect system |

---

## Validation Test Cases

Every new check must be validated with both **ST** and **RLL** neutral text.
The Reference column links to the OSS repo test that inspired the check.

### WS101 — Floating-Point Equality

```iecst
// ST: REAL equality comparison (triggers WS101)
PROGRAM Test
VAR
    r : REAL;
    flag : BOOL;
END_VAR
    flag := (r + 0.2) = 0.3;
END_PROGRAM
```

```iecst
// ST: LREAL inequality comparison (triggers WS101)
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
// RLL: CPT with REAL comparison (triggers WS101)
CPT(Flag, Motor_Speed = 100.5);
```

```iecst
// RLL: GRT/LES on REAL (triggers WS101)
GRT(Motor_Speed, 99.9)OTE(HighSpeed);
```

**Reference:** truST `crates/trust-hir/tests/semantic_type_checking/basics_and_warnings.rs` lines 457-469
**File to create:** `tests/data/invalid/WS101_float_equality.L5X`

### WS102 — Division by Literal Zero

```iecst
// ST: Division by literal zero (triggers WS102)
PROGRAM Test
VAR
    x : DINT;
    result : DINT;
END_VAR
    result := x / 0;
END_PROGRAM
```

```iecst
// ST: MOD with literal zero (triggers WS102)
PROGRAM Test
VAR
    x : DINT;
    result : DINT;
END_VAR
    result := x MOD 0;
END_PROGRAM
```

```iecst
// ST: Parenthesized zero (triggers WS102)
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
// RLL: CPT with division by zero (triggers WS102)
CPT(Dest, A / 0);
```

**Reference:** RuSTy `src/validation/tests/statement_validation_tests.rs` lines 2783-2942
**File to create:** `tests/data/invalid/WS102_div_by_zero.L5X`

### WC103 — Cyclomatic Complexity

```iecst
// ST: 15+ branching points (triggers WC103 at threshold 15)
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
// RLL: Rung with 15+ branches (triggers WC103)
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
**File to create:** `tests/data/invalid/WC103_complexity.L5X`

### EC011 — Reserved Name Collision

```iecst
// ST: AOI named TON shadows built-in (triggers EC011)
FUNCTION_BLOCK TON
VAR_INPUT
    value : INT;
END_VAR
END_FUNCTION_BLOCK
```

```iecst
// ST: AOI named CTU shadows built-in (triggers EC011)
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
// RLL: Custom AOI call with built-in name (triggers EC011)
My_TON(MyTimer, ?, ?);
```

**Implementation note:** The reserved name list must match `_BUILTIN_OPCODES` in `checks/opcodes.py` plus Rockwell's built-in type names (TON, TOF, CTU, CTD, etc.).
**Reference:** IronPLC `compiler/analyzer/src/rule_stdlib_type_redefinition.rs` lines 78-132
**File to create:** `tests/data/invalid/EC011_reserved_name.L5X`

### EC012 — Array Initializer Element Count Mismatch

```iecst
// ST: Array type with 5 elements, initialized with 3 (triggers EC012)
TYPE MyArray : ARRAY[1..5] OF INT := [1, 2, 3];
END_TYPE
```

```iecst
// ST: Array variable with 10 elements, initialized with 3 (triggers EC012)
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

**Note:** The neutral text above shows IEC 61131-3 ST syntax for illustration. In L5X, array values are stored in XML `<Data Format="Decorated"><Array>...</Array></Data>` elements (see §4.1 Reference). The actual test L5X file will have a `<Tag>` with `<Data>` containing fewer `<Element>` children than the declared `Dimensions`. The check counts `<Element>` children vs the product of the tag's dimension sizes.
**Reference:** RuSTy `src/validation/tests/array_validation_test.rs` lines 820-848, `tests/lit/single/init/array_partial_init_warning_type_and_var.st`
**File to create:** `tests/data/invalid/EC012_array_init_count.L5X`

### WS104 — Non-BOOL Condition

```iecst
// ST: IF with DINT condition (triggers WS104)
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
// ST: WHILE with DINT condition (triggers WS104)
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
// RLL: XIC/XIO always use BOOL, so WS104 is ST-only
```

**Reference:** RuSTy `src/validation/tests/statement_validation_tests.rs` lines 2109-2186
**File to create:** `tests/data/invalid/WS104_non_bool_condition.L5X`

### WS105 — Implicit Downcast

```iecst
// ST: Assign LINT to DINT (triggers WS105)
PROGRAM Test
VAR
    narrow : DINT;
    wide : LINT;
END_VAR
    narrow := wide;
END_PROGRAM
```

```iecst
// ST: Assign REAL to DINT (triggers WS105)
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
// RLL: MOV from REAL to DINT (triggers WS105)
MOV(RealVal, DintDest);
```

**Reference:** RuSTy `src/validation/tests/variable_validation_tests.rs` lines 1647-1695, `statement_validation_tests.rs` lines 1542-1720
**File to create:** `tests/data/invalid/WS105_implicit_downcast.L5X`

### WC106 — Unused POU

```iecst
// ST: Unreferenced function block (triggers WC106)
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
// RLL: Unreferenced routine (triggers WC106 — routine in L5X that's never JSR'd)
```

**Reference:** truST `crates/trust-hir/tests/semantic_type_checking/basics_and_warnings.rs` lines 301-309
**File to create:** `tests/data/invalid/WC106_unused_pou.L5X`

### WS107 — Missing ELSE

```iecst
// ST: IF without ELSE (triggers WS107)
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
// ST: CASE without ELSE (triggers WS107)
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
**File to create:** `tests/data/invalid/WS107_missing_else.L5X`

---

#### Round 1: Prefix Migration (rename only, no behavior change)

Rename all 15 existing codes and restructure into format-based subdirectories.
This is purely mechanical — nothing changes about what each check detects.

| Step | What | How | Status |
|------|------|-----|--------|
| 1 | Create dirs | `mkdir src/l5x_lint/checks/{cross,rll,st} tests/checks/{cross,rll,st}` | ✅ Done |
| 2 | Add `__init__.py` per subdir | Each imports its check modules | ✅ Done |
| 3 | Rename `_codes.py` dataclasses | `E001→EC001, E002→EC002, ..., W005→WC005` | ✅ Done |
| 4 | Move + rename 15 check files | Per table below (git mv preserves history) | ✅ Done |
| 5 | Update imports in moved files | `from l5x_lint.checks._codes import EC001` | ✅ Done |
| 6 | Update `checks/__init__.py` | Replace flat imports with subdirectory imports | ✅ Done |
| 7 | Move + rename 15 test files and test data files | `tests/checks/e001*.py` → `tests/checks/cross/test_ec001*.py`; `tests/data/invalid/E001_*.L5X` → `EC001_*.L5X`, etc. | ✅ Done |
| 8 | Update `tests/__init__.py` paths | Point to new test file locations | ⬜ N/A (no `tests/__init__.py` exists) |
| 9 | Update `AGENTS.md` test mirror section | Show new folder layout | ✅ Done |
| 10 | Run `uv run pytest tests/ -v` | All pass | ✅ Done — 347/347 |

File move table:

| From | To |
|------|----|
| `checks/e001_undefined_tag.py` | `checks/cross/ec001_undefined_tag.py` |
| `checks/e002_type_mismatch.py` | `checks/cross/ec002_type_mismatch.py` |
| `checks/e003_missing_aoi.py` | `checks/cross/ec003_missing_aoi.py` |
| `checks/e004_invalid_jsr.py` | `checks/cross/ec004_invalid_subroutine.py` |
| `checks/e005_invalid_member.py` | `checks/cross/ec005_invalid_member.py` |
| `checks/e006_array_bounds.py` | `checks/cross/ec006_array_bounds.py` |
| `checks/e007_duplicate_tag.py` | `checks/cross/ec007_duplicate_tag.py` |
| `checks/e008_aoi_circular.py` | `checks/cross/ec008_aoi_circular_dep.py` |
| `checks/e009_wrong_operand_count.py` | `checks/rll/er009_wrong_operand_count.py` |
| `checks/e010_cross_scope.py` | `checks/cross/ec010_cross_scope_violation.py` |
| `checks/w001_unused_tag.py` | `checks/cross/wc001_unused_tag.py` |
| `checks/w002_afi_rung.py` | `checks/rll/wr002_afi_rung.py` |
| `checks/w003_output_never_driven.py` | `checks/rll/wr003_output_never_driven.py` |
| `checks/w004_timer_pre.py` | `checks/rll/wr004_timer_pre.py` |
| `checks/w005_shadowed_tag.py` | `checks/cross/wc005_shadowed_tag.py` |
| `tests/checks/test_e001*.py` | `tests/checks/cross/test_ec001*.py` |
| `tests/checks/test_e009*.py` | `tests/checks/rll/test_er009*.py` |
| `tests/checks/test_w001*.py` | `tests/checks/cross/test_wc001*.py` |
| `tests/checks/test_w002*.py` | `tests/checks/rll/test_wr002*.py` |
| `tests/domain/test_errors.py` | split: `tests/checks/cross/test_codes.py` + `tests/domain/test_errors.py` |

---

#### Round 2: Type Resolver + All New Checks (~34)

After Round 1, the new subdirectory structure exists. First build the type resolver,
then add every new check from the registry (§4.4) using the template below.

**Step 0 — Prerequisite infrastructure:**

| Sub-step | What | File | Effort |
|----------|------|------|--------|
| 0a | Add `resolve_type(tag_name, program) -> DataType` to SymbolTable | `pipeline/symbols.py` | 1h |
| 0b | Add `expression_type(expr, program, symbols) -> str | None` helper | `checks/_types.py` | 1h |
| 0c | Unit tests for type resolution | `tests/pipeline/test_symbols.py` | 0.5h |
| 0d | Add `initial_values` field to `Tag`; parse `<Data Format="Decorated">` → `<Array>` → `<Element>` count in parser | `domain/models.py` + `infrastructure/parsers/base.py` | 1.5h |

See Reference Material for code examples.

**Priority checks (9):** ⚡ = type resolver  ✦ = domain model/parser extension  ⚠ = needs control flow awareness

| Order | Code | Check | Est. Effort | Status |
|-------|------|-------|-------------|--------|
| 2a | EC011 | Reserved name collision | Small | ✅ Done |
| 2b | WS101 | Float equality ⚡ | Small | ✅ Done |
| 2c | WS102 | Div by literal zero | Small | ✅ Done |
| 2d | WC103 | Cyclomatic complexity | Small | ✅ Done |
| 2e | WS105 | Implicit downcast ⚡ | Medium | ✅ Done |
| 2f | WS107 | Missing ELSE | Small | ✅ Done |
| 2g | WS104 | Non-BOOL condition ⚡ | Small | ✅ Done |
| 2h | WC106 | Unused POU | Medium | ✅ Done |
| 2i | EC012 | Array init count ✦ | Medium | ✅ Done |

**Extended candidates (25+):**

| Order | Code | Check | Source | Est. Effort | Status |
|-------|------|-------|--------|-------------|--------|
| 2j | ER013 | Invalid JMP target | RuSTy E018 | Small | ✅ Done |
| 2k | ER014 | OTL without OTU | Logix-specific | Small | ✅ Done |
| 2l | EC015 | Invalid/undeclared data type | RuSTy E052 | Small | ✅ Done |
| 2m | WS110 | Dead code after RETURN ⚠ | truST W003 | Small | ✅ Done |
| 2n | EC017 | Constant modification | truST E302 | Small | ✅ Done |
| 2o | EC013 | Duplicate JMP label | RuSTy E018 | Small | ✅ Done |
| 2p | WR006 | SUS in production | Logix-specific | Tiny | ✅ Done |
| 2q | WR005 | NOP present | Logix-specific | Tiny | ✅ Done |
| 2r | WR007 | Inputs only, no output | Logix-specific | Small | ✅ Done |
| 2s | WS108 | Statement with no effect | RuSTy E023 | Small | ✅ Done |
| 2t | WS113 | AND_THEN/OR_ELSE non-BOOL | RuSTy E133 | Small | ✅ Done |
| 2u | WS109 | FOR loop var assign | RuSTy E065 | Small | ✅ Done |
| 2v | ES001 | Invalid expression op | truST E202 | Medium | ✅ Done |
| 2w | ES002 | Duplicate CASE value | RuSTy E054 | Small | ✅ Done |

Template for each new check:

| Step | What | File |
|------|------|------|
| 0 | Extend domain model / parser if check needs new data (e.g., EC012 needs `<Data>` parsing) | `domain/models.py` + `infrastructure/parsers/base.py` |
| 1 | Add dataclass with new prefix | `checks/_codes.py` |
| 2 | Add to `LintError` union | `checks/_codes.py` |
| 3 | Create check function (`@register`) | `checks/{cross,rll,st}/ecNNN_name.py` |
| 4 | Import it in subdir `__init__.py` | `checks/{cross,rll,st}/__init__.py` |
| 5 | Create invalid L5X test data | `tests/data/invalid/EC011_reserved_name.L5X` |
| 6 | Create valid L5X test data | `tests/data/valid/EC011_reserved_name.L5X` |
| 7 | Create unit test | `tests/checks/{cross,rll,st}/test_ec011_reserved_name.py` |
| 8 | Add to parametrized integration test | `tests/test_integration.py` |
| 9 | Update opcodes if needed | `checks/opcodes.py` (for EC011) |
| 10 | `uv run pytest tests/ -v` | All pass |

---

#### Round 3: Plumbing Features

| Order | Feature | Source | Effort |
|-------|---------|--------|--------|
| 3a | Config system | truST + RuSTy | Medium |
| 3b | Related info + hints | truST | Medium |
| 3c | Sub-checker delegation | truST | Large (do at ~25 checks) |
| 3d | Dialect system | IronPLC | Large |
---

## Reference Material — Code Examples & Architecture Definitions

These code examples are referenced by the Implementation Plan above. They are not separate proposals.

### Config System — Code Example (referenced by Round 3a)

**Source patterns:** truST `DiagnosticSettings` + RuSTy `DiagnosticsConfiguration` + IronPLC `CompilerOptions`

```python
@dataclass
class LintConfig:
    warn_unused: bool = True
    warn_unreachable: bool = True
    warn_output_never_driven: bool = True
    warn_timer_pre: bool = True
    warn_shadowed: bool = True
    warn_numeric_hazards: bool = False
    warn_complexity: bool = False
    severity_overrides: dict[str, str] = field(default_factory=dict)
    rule_pack: str | None = None
    dialect: str = "rockwell"

    def apply_rule_pack(self) -> None:
        match self.rule_pack:
            case "safety":
                self.severity_overrides.update({"W004": "error", "W005": "error"})
                self.warn_numeric_hazards = True; self.warn_unreachable = True
            case "rockwell":    self.warn_numeric_hazards = False
            case "iec-61131-3": self.warn_output_never_driven = True; self.warn_complexity = True

    def diagnostic_allowed(self, code: str, severity: str) -> bool:
        match code:
            case "W001": return self.warn_unused
            case "W002": return self.warn_unreachable
            case "W003": return self.warn_output_never_driven
            case "W004": return self.warn_timer_pre
            case "W005": return self.warn_shadowed
            case "W101" | "W102": return self.warn_numeric_hazards
            case "W103": return self.warn_complexity
            case _: return True

    def resolve_severity(self, code: str, default_severity: str) -> str:
        return self.severity_overrides.get(code, default_severity)
```

### Type Resolver (Round 2 prerequisite)

**Purpose:** Enable checks that need tag/expression data types (WS101, WS104, WS105).

```python
# pipeline/symbols.py — add to SymbolTable
def resolve_type(self, name: str, program: str | None = None) -> DataType | None:
    match self.resolve(name, program):
        case Some(tag):
            return self.data_types.get(tag.data_type)
        case _:
            return None

def resolve_member_type(self, base_type: str, member: str) -> DataType | None:
    dt = self.data_types.get(base_type)
    if dt is None:
        return None
    for m in dt.members:
        if m.name == member:
            return self.data_types.get(m.data_type)
    return None
```

```python
# checks/_types.py — expression type resolution
from l5x_lint.domain.st_models import StBinaryOp, StLiteral, StTagRef

def expression_type(expr, program: str, symbols: SymbolTable) -> str | None:
    match expr:
        case StTagRef() if expr.path.segments:
            return _tag_ref_type(expr.path.segments, program, symbols)
        case StLiteral(value=int()):
            return "DINT"
        case StLiteral(value=float()):
            return "REAL"
        case StLiteral(value=bool()):
            return "BOOL"
        case StCall(name=name):
            return _call_return_type(name, symbols)
    return None

def _tag_ref_type(segments, program, symbols) -> str | None:
    base = symbols.resolve_type(segments[0].name, program)
    if base is None:
        return None
    current = base.name
    for seg in segments[1:]:
        dt = symbols.resolve_member_type(current, seg.name)
        if dt is None:
            return None
        current = dt.name
    return current
```

### Diagnostic Enhancement (Related Info + Hints)

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
    related: list[RelatedInfo] = field(default_factory=list)
    sub_diagnostics: list[Diagnostic] = field(default_factory=list)
    iec_reference: str | None = None

def suggest_did_you_mean(name: str, known_names: list[str]) -> str | None:
    candidates = [(n, levenshtein(name.lower(), n.lower())) for n in known_names]
    candidates.sort(key=lambda x: x[1])
    best_dist = candidates[0][1] if candidates else 99
    if best_dist <= 2:  return f"Did you mean '{candidates[0][0]}'?"
    if best_dist <= 4:  return f"Did you mean '{candidates[0][0]}'?"
    return None

def syntax_habit_hints(message: str) -> str | None:
    hints = {"==": "Use '=' in ST","!=": "Use '<>' in ST","&&": "Use 'AND'","||": "Use 'OR'","{": "Use '(* *)'"}
    for pattern, hint in hints.items():
        if pattern in message: return hint
    return None
```

### Sub-Checker Delegation Architecture

**Source pattern:** truST `ExprChecker`/`StmtChecker`/`CallChecker` delegation

```python
class ExprChecker:
    def check_binary_op(self, expr, symbols): ...
    def check_call(self, expr, symbols): ...

class StmtChecker:
    def check_assignment(self, stmt, symbols): ...
    def check_if(self, stmt): ...

class DeclChecker:
    def check_tag(self, tag, symbols): ...
    def check_data_type(self, dt): ...
    def check_aoi(self, aoi, symbols): ...
```

### Dialect System

**Source pattern:** IronPLC `--dialect` + `CompilerOptions`

```python
@dataclass
class DialectConfig:
    name: str
    allow_keywords_case_insensitive: bool = True
    allow_positional_args: bool = True
    allow_jsr: bool = True
    allow_wildcard_operands: bool = True
    allow_type_punning: bool = True
    allow_c_style_comments: bool = True
    allow_cross_family_widening: bool = True

DIALECT_PRESETS = {
    "rockwell": DialectConfig(name="rockwell", allow_keywords_case_insensitive=True, allow_positional_args=True, allow_jsr=True, allow_wildcard_operands=True, allow_type_punning=True, allow_c_style_comments=True),
    "iec-61131-3": DialectConfig(name="iec-61131-3", allow_keywords_case_insensitive=False, allow_positional_args=False, allow_jsr=False, allow_wildcard_operands=False, allow_type_punning=False, allow_c_style_comments=False),
    "codesys": DialectConfig(name="codesys", allow_keywords_case_insensitive=False, allow_positional_args=True, allow_jsr=False, allow_wildcard_operands=True, allow_type_punning=True, allow_c_style_comments=True),
}
```

### Updated Module Structure (Round 3 additions)

```
l5x_lint/
  domain/
    diagnostics.py               #     + RelatedInfo, sub_diagnostics, iec_reference
    errors.py                    #     LintInternalError union — unchanged
  checks/
    _codes.py                    #     + EC011, EC012, WS101-WS107, WC103, WC106
    e011_reserved_name.py
    e012_array_init_count.py
    w101_float_equality.py
    w102_div_by_zero.py
    w103_complexity.py
    w104_non_bool_condition.py
    w105_implicit_downcast.py
    w106_unused_pou.py
    w107_missing_else.py
  pipeline/
    config.py                    # 🔷 NEW — LintConfig, DialectConfig, severity overrides
    filter.py                    # 🔷 NEW — Diagnostic filter + override pipeline
  presentation/
    cli.py                       #     + --diagnostic-config, --dialect flags
    mcp_server.py                #     + config tool for agents
```

---

## Phase 4: Full Code Registry

The prefix scheme (`{E|W}{C|R|S|F}{NNN}`) and folder structure are defined in
Round 1 of the Implementation Plan above. This section contains the complete
registry of all applicable codes and the index of non-applicable OSS codes.

### 4.1 Folder Structure (Reference)

```
src/l5x_lint/checks/
  __init__.py              # Import all check modules for @register side-effects
  _codes.py                # All error/warning code dataclasses + LintError union
  _registry.py             # @register decorator, CheckFn type, check iteration
  cross/                   # Cross-format checks (EC/WC series)
    __init__.py
    ec001_undefined_tag.py
    ec002_type_mismatch.py
    ec003_missing_aoi.py
    ec004_invalid_subroutine.py      # JSR/JXR targets
    ec005_invalid_member.py          # UDT field access
    ec006_array_bounds.py
    ec007_duplicate_tag.py
    ec008_aoi_circular_dep.py
    ec009_wrong_operand_count.py
    ec010_cross_scope_violation.py
    ec011_reserved_name.py
    ec012_array_init_count.py
    ...
    wc001_unused_tag.py
    wc005_shadowed_tag.py
    wc103_cyclomatic_complexity.py
    wc106_unused_pou.py
    ...
  rll/                     # RLL-specific checks (ER/WR series)
    __init__.py
    ...
    wr002_afi_rung.py
    wr003_output_never_driven.py
    wr004_timer_pre.py
    ...
  st/                      # ST-specific checks (ES/WS series)
    __init__.py
    ...
    ws101_float_equality.py
    ws102_div_by_zero.py
    ws104_non_bool_condition.py
    ws105_implicit_downcast.py
    ws107_missing_else.py
    ...
```

Tests mirror the source layout:

```
tests/checks/
  cross/
    test_ec001_undefined_tag.py
    ...
  rll/
    test_wr002_afi_rung.py
    ...
  st/
    test_ws101_float_equality.py
    ...
  test_check_integration.py   # Parametrized smoke test for all checks
```

### 4.3 Code Migration — Current to New

| Current | New | Severity | Format | Name | Status |
|---------|-----|----------|--------|------|--------|
| E001 | EC001 | error | cross | Undefined tag reference | ✅ existing |
| E002 | EC002 | error | cross | Type mismatch | ✅ existing |
| E003 | EC003 | error | cross | Missing AOI definition | ✅ existing |
| E004 | EC004 | error | cross | Invalid subroutine target (JSR/JXR) | ✅ existing |
| E005 | EC005 | error | cross | Invalid UDT member access | ✅ existing |
| E006 | EC006 | error | cross | Array index out of bounds | ✅ existing |
| E007 | EC007 | error | cross | Duplicate tag name in scope | ✅ existing |
| E008 | EC008 | error | cross | AOI circular dependency | ✅ existing |
| E009 | ER009 | error | RLL | Wrong operand count for opcode | ✅ existing |
| E010 | EC010 | error | cross | Cross-scope tag violation | ✅ existing |
| E011 | EC011 | error | cross | Reserved name collision | ✅ done |
| E012 | EC012 | error | cross | Array initializer element count mismatch | ✅ done |
| W001 | WC001 | warning | cross | Unused tag declared | ✅ existing |
| W002 | WR002 | warning | RLL | Unreachable rung (AFI first) | ✅ existing |
| W003 | WR003 | warning | RLL | Output never driven | ✅ existing |
| W004 | WR004 | warning | RLL | Timer PRE never set | ✅ existing |
| W005 | WC005 | warning | cross | Shadowed tag name | ✅ existing |
| W101 | WS101 | warning | ST | Floating-point equality comparison | ✅ done |
| W102 | WS102 | warning | ST | Division or modulo by literal zero | ✅ done |
| W103 | WC103 | warning | cross | Cyclomatic complexity | ✅ done |
| W104 | WS104 | warning | ST | Non-BOOL IF/WHILE condition | ✅ done |
| W105 | WS105 | warning | ST | Implicit downcast in assignment | ✅ done |
| W106 | WC106 | warning | cross | Unused POU | ✅ done |
| W107 | WS107 | warning | ST | Missing ELSE clause on IF/CASE | ✅ done |
| — | ER013 | error | RLL | Invalid JMP target label | ✅ done |
| — | ER014 | error | RLL | OTL without OTU (unbalanced latch) | ✅ done |
| — | WS121 | warning | ST | Statement with no effect | 🟡 candidate |
| — | WC122 | warning | cross | Empty routine body | 🟡 candidate |
| — | WS123 | warning | ST | Literal overflow for target type | 🟡 candidate |
| ... | ... (see full registry below) | | | | |

### 4.4 Complete Error/Warning Code Registry

Every diagnostic code from the three analyzed OSS repos, mapped to l5x-lint's prefix scheme.
Codes are grouped by applicability. `—` in the l5x-lint column means the check does not apply to Logix L5X/L5K (reason given).

#### Cross-Format Errors (EC001+)

| l5x-lint | Name | Format | OSS Source(s) | OSS Code(s) | Description | L5X Test Example | Prio |
|----------|------|--------|---------------|-------------|-------------|-------------------|------|
| EC001 | Undefined tag reference | cross | truST, RuSTy, IronPLC | truST E101, RuSTy E048, IronPLC P4001 | Tag referenced in rung/ST but not declared in any scope | `XIC(DoesNotExist)OTE(Out)` | H |
| EC002 | Type mismatch | cross | truST, RuSTy, IronPLC | truST E201, RuSTy E031/E037/E051, IronPLC P4012 | Operand/expression type incompatible with expected type | `TON(MyDINT,?,?,?)` | H |
| EC003 | Missing AOI definition | cross | truST, IronPLC | truST E103, IronPLC P4015 | Called instruction not in built-in opcodes and no matching AOI def | `MyUndefinedAOI(Arg1,Arg2)` | H |
| EC004 | Invalid subroutine target | cross | RuSTy, IronPLC | RuSTy E048, IronPLC P4021 | JSR/JXR targets a routine that doesn't exist in any program | `JSR(NoSuchRoutine,0)` | H |
| EC005 | Invalid UDT member access | cross | truST, RuSTy, IronPLC | truST E107, RuSTy E048, IronPLC P2001 | Tag member path refers to nonexistent UDT field | `MyTag.NonExistentField` | H |
| EC006 | Array index out of bounds | cross | truST, RuSTy, IronPLC | truST E303, RuSTy E053/E058/E097, IronPLC P2013 | Array index exceeds declared dimension | `MyArr[10]` on `ARRAY[0..9]` | H |
| EC007 | Duplicate tag name in scope | cross | truST, RuSTy, IronPLC | truST E104/E108, RuSTy E004/E021, IronPLC P2007 | Two tags with same name in same scope | Two `MyTag : DINT` in same scope | H |
| EC008 | AOI circular dependency | cross | truST, RuSTy | truST E305, RuSTy E121 | AOIs form a recursive call chain | AOI_A→AOI_B→AOI_A | H |
| EC009 | Wrong operand count | cross | truST, RuSTy, IronPLC | truST E204, RuSTy E032, IronPLC P4025 | Opcode/call given wrong number of operands/args | `XIC()` (0 of 1 operands) | H |
| EC010 | Cross-scope tag violation | cross | truST, RuSTy | truST E101, RuSTy E028/E099 | Program-scoped tag accessed from different program | Program_A.MyTag in Program_B | H |
| EC011 | Reserved name collision | cross | RuSTy, IronPLC | RuSTy E138, IronPLC P4015 | User-defined name shadows built-in instruction/type | AOI named `TON` | H | ✅ |
| EC012 | Array init element count | cross | RuSTy | RuSTy E043/E127 | Initializer element count ≠ array dimension | `ARRAY[1..5]:=[1,2,3]` | M | ✅ |
| EC013 | Duplicate label (JMP target) | cross | RuSTy | RuSTy E018 | Two JMP/LBL instructions share the same label | `LBL(Mark); LBL(Mark)` | M | ✅ |
| EC014 | Unresolved constant expression | cross | RuSTy | RuSTy E033 | CONSTANT initializer references non-constant values | `CONST X : DINT := Y` where Y is not CONSTANT | L |
| EC015 | Invalid/undeclared data type | cross | RuSTy, IronPLC | RuSTy E052, IronPLC P2008 | Tag declared with a type that doesn't exist | `MyTag : NonExistentType` | H | ✅ |
| EC016 | Invalid array range declaration | cross | RuSTy | RuSTy E008/E097 | Array range bounds are malformed or non-integer | `ARRAY[a..z]` with non-integer bounds | M | |
| EC017 | Modification of constant tag | cross | truST, RuSTy | truST E302, RuSTy E036 | Assignment to a CONSTANT-declared tag | `MyConst := 5` where MyConst is CONSTANT | M | ✅ |
| EC018 | Empty project or POU | cross | truST, IronPLC | truST W009, IronPLC P9002 | Controller has no programs or a program has no routines | Empty Routine element | L |

#### Cross-Format Warnings (WC001+)

| l5x-lint | Name | Format | OSS Source(s) | OSS Code(s) | Description | L5X Test Example | Prio |
|----------|------|--------|---------------|-------------|-------------|-------------------|------|
| WC001 | Unused tag declared | cross | truST | truST W001 | Tag is declared but never read or written | `MyTag : DINT` never used | H |
| WC005 | Shadowed tag name | cross | truST | truST W006 | Program tag hides controller-scoped tag with same name | Ctrl.MyTag + Prog.MyTag | H |
| WC103 | Cyclomatic complexity | cross | truST | truST W008 | Routine has ≥15 branching points (IFs, CASEs, branches) | 16 IF statements in one routine | M |
| WC106 | Unused program/routine | cross | truST | truST W009 | Program/routine is never referenced by JSR or configured as Main | `MyProgram` with no calls to it | M |
| WC107 | Empty IF/CASE body | cross | RuSTy | RuSTy E090 | Conditional branch contains no statements | `IF x THEN END_IF` | L |
| WC108 | Deprecated instruction used | cross | truST | truST W007 | Instruction is deprecated in current Logix version | Reserved for future | L |

#### RLL-Specific Errors (ER001+)

| l5x-lint | Name | Format | OSS Source(s) | OSS Code(s) | Description | L5X Test Example | Prio |
|----------|------|--------|---------------|-------------|-------------|-------------------|------|
| ER009 | Wrong operand count for opcode | RLL | truST, RuSTy, IronPLC | truST E204, RuSTy E032, IronPLC P4025 | RLL opcode called with wrong number of operands | `XIC()` (needs 1) | H |
| ER013 | Invalid JMP target label | RLL | RuSTy, IronPLC | RuSTy E018, IronPLC P4021 | JMP to label that has no matching LBL in the routine | `JMP(GoneLabel)` with no `LBL(GoneLabel)` | H | ✅ |
| ER014 | OTL without OTU (unbalanced latch) | RLL | — | — (Logix-specific) | OTL output is never unlatched by a corresponding OTU | `OTL(MyBit)` but no `OTU(MyBit)` in any rung | M | ✅ |
| ER015 | MCR zone without matching BST/BND | RLL | — | — (Logix-specific) | MCR instruction without beginning/end branch markers | `MCR()` alone with no matching MCR | L |
| ER016 | FAL/FSC with incomplete operands | RLL | — | — (Logix-specific) | File instruction missing required mode/control/destination | `FAL()` with 0 args | M |

#### RLL-Specific Warnings (WR001+)

| l5x-lint | Name | Format | OSS Source(s) | OSS Code(s) | Description | L5X Test Example | Prio |
|----------|------|--------|---------------|-------------|-------------|-------------------|------|
| WR002 | Unreachable rung (AFI first) | RLL | — | — (Logix-specific) | Rung begins with AFI, all following rungs are dead too | `AFI()` as first instruction | H |
| WR003 | Output never driven | RLL | truST | truST W003 (varies) | Tag used only in XIC/XIO, never in OTE/OTL/OTU | `XIC(MyTag)` in 10 rungs, no `OTE(MyTag)` | H |
| WR004 | Timer PRE never set (zero) | RLL | truST | truST W003 (varies) | Timer preset is 0, so timer will never time out | `TON(MyTimer,?,0)` | H |
| WR005 | NOP instruction present | RLL | — | — (Logix-specific) | NOP instructions are no-ops that indicate dead code | `NOP()` in rung | L | ✅ |
| WR006 | SUS instruction present in production | RLL | — | — (Logix-specific) | SUS instruction is a debug breakpoint, should not be in production | `SUS(MyStr)` | L | ✅ |
| WR007 | Rung with inputs only, no output | RLL | — | — (Logix-specific) | Rung has XIC/XIO but no OTE/OTL/OTU or other output | `XIC(A)XIO(B)` — no output | L | ✅ |
| WR008 | COP/CPS overlapping source/dest | RLL | — | — (Logix-specific) | Copy instruction where source and destination overlap | `COP(MyArr[0],MyArr[1],10)` | L |
| WR009 | GSV/SSV invalid object class | RLL | — | — (Logix-specific) | GSV/SSV references unknown object class | `GSV(InvalidClass,??,?)` | M |

#### ST-Specific Errors (ES001+)

| l5x-lint | Name | Format | OSS Source(s) | OSS Code(s) | Description | L5X Test Example | Prio |
|----------|------|--------|---------------|-------------|-------------|-------------------|------|
| ES001 | Invalid expression operation | ST | truST, RuSTy | truST E202, RuSTy E066 | Operation not valid for the operand types (e.g., string + DINT) | `result := "abc" + 5;` | M | ✅ |
| ES002 | CASE with duplicate value | ST | RuSTy | RuSTy E054 | CASE statement has two branches with same selector value | `CASE x OF 1: a:=1; 1: a:=2; END_CASE` | M | ✅ |
| ES003 | FOR loop with out-of-range bounds | ST | RuSTy | RuSTy E065/E097 | FOR loop start/end/repeat values outside valid range | `FOR i:=0 TO 9999999999 DO ... END_FOR` | L |
| ES004 | Invalid escape sequence in string | ST | RuSTy | RuSTy E124 | String literal contains unrecognized escape sequence | `s := "hello\xJ";` | L |
| ES005 | Non-constant array boundary | ST | RuSTy | RuSTy E117 | Array declaration uses non-constant expression for bound | `ARRAY[n..m]` where n,m are variables | L |

#### ST-Specific Warnings (WS001+)

| l5x-lint | Name | Format | OSS Source(s) | OSS Code(s) | Description | L5X Test Example | Prio |
|----------|------|--------|---------------|-------------|-------------|-------------------|------|
| WS101 | Floating-point equality comparison | ST | truST | truST W013 | REAL/LREAL values compared with = or <> | `IF r = 0.3 THEN` | H | ✅ |
| WS102 | Division/modulo by literal zero | ST | truST | truST W014, RuSTy E123 | Division or MOD by literal zero | `result := x / 0;` | H | ✅ |
| WS104 | Non-BOOL condition in IF/WHILE | ST | RuSTy | RuSTy E094/E096 | IF/WHILE condition is DINT/REAL, not BOOL | `IF myDINT THEN` | L | ✅ |
| WS105 | Implicit downcast in assignment | ST | RuSTy, truST | RuSTy E067, truST W005 | Assigning wider type to narrower type truncates | `narrowDINT := wideLINT` | M | ✅ |
| WS107 | Missing ELSE clause | ST | truST | truST W004 | IF or CASE without ELSE branch | `IF x > 0 THEN y:=1; END_IF` | L | ✅ |
| WS108 | Statement with no effect | ST | RuSTy | RuSTy E023/E060 | Expression statement that does nothing (just a value) | `x + 1;` alone as statement | L | ✅ |
| WS109 | Assignment to FOR loop variable | ST | RuSTy | RuSTy E065 | Modifying loop counter inside FOR loop body | `FOR i:=1 TO 10 DO i:=i+1; END_FOR` | L | ✅ |
| WS110 | Return/EXIT followed by dead code | ST | truST | truST W003 | Statements after RETURN or EXIT are unreachable | `RETURN; x := 1;` | M | ✅ |
| WS111 | Literal overflow for target type | ST | RuSTy | RuSTy E053/E039 | Integer/real literal exceeds range of destination type | `smallSINT := 999;` (SINT max 127) | L | |
| WS112 | Empty CASE branch body | ST | RuSTy | RuSTy E090 | CASE branch contains no statements | `CASE x OF 1: ; 2: y:=1; END_CASE` | L | |
| WS113 | AND_THEN/OR_ELSE with non-BOOL operand | ST | RuSTy | RuSTy E133 | Short-circuit operator used with non-BOOL type | `x AND_THEN y` where x is DINT | L | ✅ |
| WS114 | Implicit cast in mixed-type expression | ST | RuSTy, truST | RuSTy E067, truST W005 | Mixed numeric types in expression (DINT+REAL) get implicit cast | `result := dintVal + realVal;` | L | |

---

### 4.5 Non-Applicable OSS Code Index

Codes from OSS repos that do not map to Logix L5X/L5K, grouped by reason.
Based on Rockwell documentation: 1756-PM018I (IEC 61131-3 Compliance, March 2022)
and 1756-PM007 (Structured Text Programming Manual).
These are listed here for completeness and to prevent repeated analysis.

**Note on reference/by-reference semantics:** Logix InOut AOI parameters are
passed by reference (per 1756-PM018I §42.10a). There is no standalone
`REFERENCE TO <type>` declaration or `REF=` assignment syntax, but RuSTy
checks around by-reference assignment (`E042`, `E049`) have partial analogues
in InOut parameter usage. They are noted below with "🟡 partial" instead of N/A
where applicable.

#### truST Platform — Non-Applicable

| Code(s) | Name | Category | Reason N/A in Logix |
|---------|------|----------|---------------------|
| E001-E003 | UnexpectedToken, MissingToken, UnclosedBlock | Syntax | Handled by Lark parser at parse-failure boundary; reported as STParseError/RLLParseError, not user-facing diagnostic codes |
| E102 | UndefinedType | Type | Merged into EC015 (invalid/undeclared data type) |
| E103 | UndefinedFunction | Name resolution | Logix AOIs don't have return values; merged into EC003 (missing AOI definition) |
| E105 | CannotResolve | Name | Merged into EC001 (undefined tag) |
| E106 | InvalidIdentifier | Name | Handled by Lark parser rejection of invalid identifiers |
| E202 | InvalidOperation | Type | Niche — non-BITWISE operation on BOOL, etc. Low value for Logix |
| E203 | IncompatibleAssignment | Type | Merged into EC002 (type mismatch) |
| E205 | InvalidArgumentType | Type | Merged into EC002 (type mismatch) |
| E206 | MissingReturn | Control flow | Functions don't exist in Logix ST; AOIs can't have return values |
| E207 | InvalidReturnType | Control flow | Same as above — no function return types |
| E301 | InvalidAssignmentTarget | Control flow | Merged into EC017 (constant modification) |
| E304 | OutOfRange | Type | Merged into EC006 (array bounds) |
| E306-E307 | InvalidTaskConfig, UnknownTask | Configuration | Logix has no ST-level task configuration in L5X |
| W002 | UnusedParameter | Declaration | Low value — AOI parameters are often template-wired |
| W005 | ImplicitConversion | Type | Merged into WS105 (implicit downcast) |
| W007 | Deprecated | Style | Reserved for future WC108 |
| W010 | NondeterministicTimeDate | Environment | Edge case — GET_DATE_TIME() etc. not common in Logix ST |
| W011 | NondeterministicIo | Environment | I/O mapping is external to logic |
| W012 | SharedGlobalTaskHazard | Concurrency | Logix has no ST-level task model |
| I001 | Simplification | Style | Hint — merges into WS108 (statement with no effect) |
| I002 | StyleSuggestion | Style | Hint — style preferences out of scope for v1 |

#### RuSTy — Non-Applicable

| Code(s) | Name | Category | Reason N/A in Logix |
|---------|------|----------|---------------------|
| E001 | General Error | Catch-all | Internal — not a user-facing check |
| E002 | General IO Error | IO | Pipeline-level failure, not a diagnostic check |
| E003 | Parameter Error | CLI | Not about L5X content |
| E005 | Generic LLVM Error | Codegen | LLVM codegen doesn't exist in l5x-lint |
| E006-E007, E009-E012, E026-E030 | Parser errors (missing/ unexpected tokens, mismatched parens, invalid literals) | Lexer/Parser | Handled by Lark at parse boundary; reported as pipeline errors, not diagnostics |
| E013-E016 | Style warnings (underscores, parens type, pointer non-standard, return default) | Style | Low-value IEC style preferences; pointer warnings N/A |
| E017-E019, E020, E025 | Class restrictions (implementations, IN_OUT, return type) | POU/Class | Logix has no ST class concept |
| E022 | Missing action container | POU | Logix ST has no action containers |
| E024 | Invalid pragma location | Preprocessor | Logix ST has no pragmas |
| E033-E035 | Constant resolution errors | Constants | Merged into EC014 |
| E038 | Missing type | Type | Merged into EC015 |
| E040 | Non-standard enum variant | Enum | Logix has no IEC enums (uses UDTs instead) |
| E041 | Invalid variable initializer | Declaration | Merged into EC012 / type mismatch |
| E042 | Assignment to reference | Reference | 🟡 Partial — Logix InOut parameters ARE by-reference (1756-PM018I §42). No standalone REFERENCE TO type, but AOI InOut assignment checks could adapt this |
| E044-E047 | VLA (variable-length array) errors | VLA | Logix doesn't support VLAs |
| E049 | Illegal reference access | Reference | 🟡 Partial — same as E042, by-reference InOut means illegal access checks could apply to InOut parameters |
| E050 | Expression not assignable | Assignment | Merged into ES001 |
| E055-E059 | Direct access errors (%I/%Q) | Hardware | Logix addresses differently; %-notation not used in ST |
| E060 | Direct access with % | Info | Same as above — N/A |
| E061-E063 | Expected literal, Invalid/Unknown Nature | Pragma | Logix ST has no Nature pragmas |
| E064 | Unresolved generic | Generic | Logix has no generics |
| E068-E070 | Pointer/reference deref, address-of | Pointer | 🟡 Partial — InOut passes by reference (no explicit dereference syntax). ADR/REF operators not in Logix ST. Deref of InOut params may have analogue |
| E071-E089 | Codegen/LLVM errors | Codegen | LLVM codegen N/A |
| E091 | *not described* | — | Not clearly applicable |
| E092 | Info-level diagnostic | Info | Low priority |
| E093 | Warning-level diagnostic | Warning | Not clearly applicable |
| E095 | Action call without () | Call | Logix ST action calls N/A |
| E098 | Invalid REF= assignment | Reference | N/A — Logix has no REF= assignment syntax. InOut by-reference is configured via the AOI parameter editor, not in ST syntax |
| E099-E109 | VAR_CONFIG / template variable / hardware binding | Hardware config | Logix handles hardware binding in I/O configuration, not ST |
| E110-E114, E118 | Interface implementation errors | Interface | Logix has no interface concept in ST |
| E115-E116 | Property in unsupported POU | Property | Logix has no ST properties |
| E119-E120 | THIS/SUPER keyword | Keyword | Logix ST doesn't support THIS/SUPER |
| E122 | Invalid enum base type | Enum | Logix has no IEC enums |
| E124 | Invalid escape sequence | Literal | Merged into ES004 |
| E125-E126, E129 | Interface polymorphism | Interface | Logix has no interface concept |
| E128 | Invalid nested property assignment | Property | Logix has no ST properties |
| E130 | Array size exceeds limit | Array | Merged into EC006 |
| E131 | Positional + named arg collision | Call | Low value — Logix doesn't use named arguments in ST calls |
| E132 | Mixing implicit/explicit call params | Call | Low value |
| E134 | Invalid --hwmap-file argument | CLI | CLI validation, not L5X content |
| E135 | => on non-output parameter | Call | 🟡 Partial — Logix AOI calls use positional args, but `=>` (formal call) IS supported for AOIs. Low value |
| E136 | Incomplete hardware address | Hardware | N/A — hardware binding is not ST-level |
| E137 | FB-level VAR_TEMP from METHOD | POU | Logix has no method concept |
| E139 | Linker invocation failed | Build | Build tooling, not L5X content |
| E140 | `:=` on output parameter | Call | 🟡 Partial — Logix AOI calls support `:=` for output parameters in formal call syntax. Low value for RLL (positional) but applicable to ST AOI calls |

#### Logix-Specific Limitations Not in Any OSS Repo

These are real Logix ST constraints documented in 1756-PM007 and 1756-PM018I
that no OSS repo checks (because they target Codesys/TwinCAT, where these
limits don't exist):

| Constraint | Documented In | Description | Check Candidate |
|------------|--------------|-------------|-----------------|
| No REPEAT loop | 1756-PM007 Ch.1 | `REPEAT ... UNTIL ... END_REPEAT` not available | WS115 |
| No GOTO statement | 1756-PM007 Ch.1 | `GOTO` not available in Logix ST | WS116 |
| No IEC ENUM types | 1756-PM018I §72 | CASE selectors must be integer literals, not enum names | — |
| OR/XOR limit | TechNote 64904 | Max 6 OR/XOR operators per expression | WS117 |
| CASE constant restriction | 1756-PM001 | CASE selectors cannot be constants or tags, only immediate integers | WS118 |
| `SIN`/`COS`/`SORT` etc. are instructions not functions | 1756-PM007 | Math functions use instruction syntax, not `FUNC(args)` | — |
| Non-retentive assignment `S:=` | 1756-PM007 | Tag is reset to 0 on entering Run mode or SFC step transition | — |

#### IronPLC — Non-Applicable

| Code(s) | Name | Category | Reason N/A in Logix |
|---------|------|----------|---------------------|
| P0001-P0007 | Syntax/XML errors (OpenComment, SyntaxError, UnexpectedToken, CStyleComment, UnexpectedElement, XmlMalformed, XmlSchemaViolation) | Lexer/XML | Lark handles syntax; schema validation is separate; C-style comments allowed in Logix |
| P0008 | SfcMissingInitialStep | SFC | SFC out of scope for v1 |
| P0009 | TwinCatMalformed | TwinCAT | Logix uses L5X, not TwinCAT XML |
| P0010 | Std2013Feature | Standard | IEC 2013 features not relevant to Logix |
| P0011 | EmptyVarBlock | Declaration | Low value — merged into general empty POU check |
| P2002-P2006 | Subrange/Enum errors (subrange, enum duplicate, enum undeclared, enum recursive, enum value not defined) | Type | Logix uses UDTs, not IEC subranges/enums |
| P2009-P2012 | Parent enum / incomplete type / wrong type / cycle errors | Type | Logix UDT model is different |
| P2014-P2036 | Type declaration errors (duplicate member types, init value types, string length, array of arrays, etc.) | Type | Logix-specific type handling is different; merged into EC002/EC006 |
| P4002-P4011, P4013-P4014 | Scope/semantic errors (various POUs, duplicate POU, etc.) | Scope | Merged into EC010/EC007 |
| P4016-P4020 | Various semantic checks | Semantic | Logix doesn't have VAR RETAIN / VAR CONSTANT in the same way |
| P4022-P4033 | Reference/array/scope errors | Various | Overlaps with existing cross-format codes |
| P6001-P6008 | I/O / filesystem errors | IO | Not L5X content |
| P8001 | MCP input validation | CLI | Tooling, not diagnostics |
| P9001 | UnsupportedStdLibType | Library | Merged into EC015 |
| P9003 | XmlBodyTypeNotSupported | Format | Merged into EC019 (unsupported body type) |
| P9998-P9999 | Internal/NotImplemented | Internal | Not user-facing |

---

### 4.6 Implementation Priority

| Round | Code | Check | Effort | Impact | Source |
|-------|------|-------|--------|--------|--------|
| 1 | — | Prefix scheme definition + migration | Medium | Medium | — |
| 2a | EC011 | Reserved name collision | Small | High | RuSTy E138, IronPLC P4015 |
| 2b | WS101 | Float equality | Small | Medium | truST W013 |
| 2c | WS102 | Div by literal zero | Small | Medium | truST W014, RuSTy E123 |
| 2d | WC103 | Cyclomatic complexity | Small | Medium | truST W008 |
| 2e | WS105 | Implicit downcast | Medium | Medium | RuSTy E067, truST W005 |
| 2f | WS107 | Missing ELSE | Small | Low | truST W004 |
| 2g | WS104 | Non-BOOL condition | Small | Low | RuSTy E094/E096 |
| 2h | EC012 | Array init count | Medium | Low | RuSTy E043/E127 |
| 2i | WC106 | Unused POU | Medium | Medium | truST W009 |
| 2j | ER013 | Invalid JMP target | Small | Medium | RuSTy E018 |
| 2k | ER014 | OTL without OTU | Medium | Medium | Logix-specific |
| 2l | EC015 | Invalid/undeclared data type | Small | High | RuSTy E052, IronPLC P2008 |
| 2m | WS110 | Dead code after RETURN | Small | Low-medium | truST W003 |
| 2n | EC017 | Constant modification | Small | Medium | truST E302, RuSTy E036 |
| 2o | EC013 | Duplicate JMP label | Small | Medium | RuSTy E018 |
| 2p | WR006 | SUS instruction in production | Small | Low | Logix-specific |
| 2q | WR005 | NOP instruction present | Tiny | Low | Logix-specific |
| 2r | WR007 | Rung with inputs only | Small | Low | Logix-specific |
| 2s | WS108 | Statement with no effect | Small | Low | RuSTy E023 |
| 2t | WS113 | AND_THEN/OR_ELSE with non-BOOL | Small | Low | RuSTy E133 |
| 2u | WS109 | FOR loop var assignment | Small | Low | RuSTy E065 |
| 2v | ES001 | Invalid expression operation | Medium | Medium | truST E202, RuSTy E066 |
| 2w | ES002 | Duplicate CASE value | Small | Medium | RuSTy E054 |
| — | 2x–2z | Remaining candidates from §4.4 tables | various | — | — |
| 3a | — | Config system | Medium | High | truST + RuSTy |
| 3b | — | Related info + hints | Medium | High | truST |
| 3c | — | Sub-checker delegation | Large | Medium | truST |
| 3d | — | Dialect system | Large | High | IronPLC |

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


