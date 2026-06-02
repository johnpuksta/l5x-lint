# l5x-lint

Semantic linter for Rockwell Logix L5X PLC programs. Parses the controller XML for project structure (tags, data types, routines, AOIs) and builds ASTs from the neutral text embedded within `<CData>` sections for deeper semantic analysis of RLL and ST routine bodies.

## Architecture

Clean architecture with four layers under `src/`:

| Layer | Directory | Role |
|-------|-----------|------|
| **domain** | `src/domain/` | Pure business logic. Check rules, symbol resolution, dialect config, core models. Zero external dependencies. |
| **application** | `src/application/` | Use cases and orchestration. `analyze()` is the entry point; `config.py` manages rule packs and severity overrides. |
| **infrastructure** | `src/infrastructure/` | External adapters. L5X XML parsing, Lark-based parsers for RLL neutral text and ST, XSD validation. |
| **presentation** | `src/presentation/` | CLI and MCP server glue. `cli.py` defines the `validate` subcommand. |

Cross-layer flow: `CLI → parse_l5x (infra) → analyze (application) → run_checks (domain) → diagnostics → CLI`

## Supported Neutral Text Types

Routine bodies are extracted from XML `<CData>` sections and parsed into ASTs:

| Type | Content | Parser |
|------|---------|--------|
| **RLL** | Rung-based ladder logic with instructions, operands, and branching | Lark grammar → AST of rungs, branches, instructions, and operands |
| **ST** | Structured Text — IEC 61131-3 statements (IF, CASE, FOR, WHILE, assignments, etc.) | Lark grammar → AST of expressions, statements, and control flow |

## Error Codes

Codes follow a prefix convention indicating severity and origin:

| Prefix | Severity | Source | Count |
|--------|----------|--------|-------|
| `EC` | error | cross-program tag/routine analysis | 18 |
| `ER` | error | RLL (ladder logic) | 5 |
| `ES` | error | ST (structured text) | 3 |
| `WC` | warning | cross-program tag/routine analysis | 6 |
| `WR` | warning | RLL (ladder logic) | 8 |
| `WS` | warning | ST (structured text) | 15 |
| `EX` | error | infrastructure (parse failures, internal crashes) | 2 |

### Cross-program Errors (EC*)

| Code | What it flags |
|------|---------------|
| EC001 | Undefined tag reference |
| EC002 | Type mismatch in instruction operands |
| EC003 | Missing AOI definition |
| EC004 | Invalid JSR target (routine not found) |
| EC005 | Invalid UDT member access |
| EC006 | Array index out of bounds |
| EC007 | Duplicate tag name in scope |
| EC008 | AOI circular dependency |
| EC010 | Cross-scope tag violation |
| EC011 | Reserved name collision with built-ins |
| EC012 | Array initializer element count mismatch |
| EC013 | Duplicate JMP label |
| EC014 | Constant tag with no initializer |
| EC015 | Invalid/undeclared data type |
| EC016 | Invalid array dimension |
| EC017 | Modification of constant tag |
| EC018 | Empty controller/program (no routines) |

### RLL Errors (ER*)

| Code | What it flags |
|------|---------------|
| ER009 | Wrong operand count for instruction |
| ER013 | Invalid JMP target (label not found) |
| ER014 | OTL without corresponding OTU |
| ER015 | Unpaired MCR instruction |
| ER016 | Incomplete FAL/FSC instruction |

### ST Errors (ES*)

| Code | What it flags |
|------|---------------|
| ES001 | Invalid expression operation (e.g. string + DINT) |
| ES002 | Duplicate CASE value |
| ES003 | FOR loop bound out of range |

### Cross-program Warnings (WC*)

| Code | What it flags |
|------|---------------|
| WC001 | Unused tag (declared but never referenced) |
| WC005 | Shadowed tag (program tag hides controller tag) |
| WC103 | Cyclomatic complexity exceeds threshold |
| WC106 | Unused POU (defined but never called) |
| WC107 | Empty branch body in IF/CASE |
| WC108 | Deprecated instruction in use |

### RLL Warnings (WR*)

| Code | What it flags |
|------|---------------|
| WR002 | Rung starts with AFI (unreachable) |
| WR003 | Output tag used only as input (never driven) |
| WR004 | Timer PRE is never set (stays 0) |
| WR005 | NOP instruction present (dead/debug code) |
| WR006 | SUS instruction in production code |
| WR007 | Rung has inputs but no output (no effect) |
| WR008 | COP/CPS source and destination overlap |
| WR009 | Unknown GSV/SSV object class |

### ST Warnings (WS*)

| Code | What it flags |
|------|---------------|
| WS101 | Floating-point equality comparison (unreliable) |
| WS102 | Division by literal zero |
| WS104 | Non-BOOL condition in IF/WHILE/REPEAT/UNTIL |
| WS105 | Implicit downcast losing precision |
| WS107 | Missing ELSE branch |
| WS108 | Statement with no effect |
| WS109 | Assignment to FOR loop variable inside loop |
| WS110 | Dead code after RETURN/EXIT |
| WS111 | Literal may overflow target type |
| WS112 | Empty CASE branch body |
| WS113 | Non-BOOL operand for AND_THEN/OR_ELSE |
| WS114 | Implicit cast in mixed-type expression |
| WS115 | REPEAT loop (not supported by Logix) |
| WS116 | GOTO statement (not supported by Logix) |
| WS117 | OR/XOR expression may exceed Logix operand limit |
| WS118 | CASE value is not a compile-time constant |

## CLI Usage

```
l5x-lint validate <file> [options]
```

| Option | Values | What it does | Example |
|--------|--------|--------------|---------|
| `--json` | — | Emit machine-readable output as a JSON object with `passed`, `error_count`, `warning_count`, and `diagnostics` array | `l5x-lint validate bench.L5X --json` |
| `--rule-pack` | `none`, `safety`, `rockwell`, `iec-61131-3` | Apply a preset group of rule configurations — `none` disables all rule packs, `safety` enables safety-critical checks, `rockwell` applies Rockwell-specific best practices, `iec-61131-3` applies IEC standard rules | `l5x-lint validate bench.L5X --rule-pack safety` — promotes float-equality and unreachable-rung warnings to errors |
| `--dialect` | `rockwell`, `iec-61131-3`, `codesys` | Select the PLC target dialect so checks can adapt their behavior per-platform (e.g. differences in data type sizes, supported instructions) | `l5x-lint validate bench.L5X --dialect iec-61131-3` — flags case-insensitive keywords, JSR, and positional args as violations |
| `--enable-warning` | `numeric`, `complexity` | Activate a warning category that is suppressed by default — `numeric` enables numeric-style checks, `complexity` enables cyclomatic complexity checks | `l5x-lint validate bench.L5X --enable-warning complexity` — reports WC103 for routines exceeding the complexity threshold |
| `--disable-warning` | `unused`, `unreachable`, `output`, `timer`, `shadowed`, `numeric`, `complexity`, `conversion`, `missing-else` | Suppress an entire warning category — useful to silence noisy rule groups without individual severity overrides | `l5x-lint validate bench.L5X --disable-warning unused` — suppresses WC001 (unused tag) and WC106 (unused POU) |
| `--severity-override` | `<code>=<severity>` | Override the severity of a specific diagnostic code — severity can be `error`, `warning`, `info`, or `off` | `l5x-lint validate bench.L5X --severity-override WR004=off --severity-override WS101=error` — silences timer-PRE checks, promotes float-equality to error |

Exit code: 0 if no errors, 1 if errors or parse failure.

The CLI parses the L5X file via `parse_l5x()` (infrastructure), then runs `analyze()` (application) which invokes all registered checks (domain). Diagnostics are printed with location context showing `program/routine:rung (XML line)`.

## Tests

`tests/unit/` mirrors `src/` structure exactly:

```
src/domain/checks/cross/ec001_undefined_tag.py
  → tests/unit/domain/checks/cross/test_ec001_undefined_tag.py

src/application/analyze.py
  → tests/unit/application/test_analyze.py

src/infrastructure/adapter.py
  → tests/unit/infrastructure/test_adapter.py

src/presentation/cli.py
  → tests/unit/presentation/test_cli.py
```

Every module under `src/` has a corresponding `test_` file at the same relative path under `tests/unit/`. Benchmarks live in `tests/benchmarks/`. Run with `uv run pytest tests/unit tests/benchmarks -v`.
