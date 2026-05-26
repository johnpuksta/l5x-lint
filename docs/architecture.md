# Architecture — Functional Pipeline with Ports & Adapters

## Principles

1. **Functional core, imperative shell** — all business logic is pure functions returning `Result` or `list[Diagnostic]`. IO (file reading, MCP server) lives at the edges.
2. **Railway Oriented Programming** — each step returns `Result[T, LintError]`. Composition via `flow` + `bind`, not try/except.
3. **No None** — `Maybe[Tag]` instead of `Tag | None`. Forces explicit handling.
4. **Typed errors** — `LintError` is a union type, not a string.
5. **One function per check** — each E/W code is a standalone pure function, easy to test in isolation.

---

## Stack

| Tool | Purpose |
|------|---------|
| `returns` | `Result`, `Maybe`, `flow`, `pipeline` for functional composition |
| `lark` | RLL neutral text grammar + parser |
| `jvalenzuela/l5x` | L5X XML parsing (wrapped in adapter) |
| `ruff` | Code formatting + linting |
| `uv` | Package management |
| `pytest` | Testing |

---

## Module Structure

```
l5x_lint/
  __init__.py
  
  domain/                        # Pure data types — zero dependencies
    models.py                    # Tag, DataType, Routine, ParsedRung, etc.
    diagnostics.py               # Diagnostic, Location, Severity
    errors.py                    # LintError (typed union for Result error type)
    symbol_table.py              # SymbolTable, Scope (pure query methods)
    type_system.py               # Type compatibility matrix, member resolution

  checks/                        # One pure function per E/W code
    e001_undefined_tag.py        # resolve_tag → Failure[LintError.E001]
    e002_type_mismatch.py        # check operands → list[Diagnostic]
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
    analyze.py                   # Compose all checks into a single pipeline
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

## Data Flow

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

---

## Functional Patterns

### Result for fallible operations

```python
from returns.result import Result, Success, Failure
from returns.pipeline import flow
from returns.pointfree import bind

def resolve_tag(name: str, scope: SymbolTable) -> Result[Tag, LintError]:
    match scope.lookup(name):
        case Maybe.empty: return Failure(LintError.E001(name))
        case Maybe.some(tag): return Success(tag)

# Composed via pipeline:
def check_rung(rung: ParsedRung, scope: SymbolTable) -> list[Diagnostic]:
    return flow(
        rung,
        extract_tag_refs,
        bind(lambda refs: validate_refs(refs, scope)),
        bind(lambda _: check_operand_types(rung, scope)),
    )
```

### Maybe instead of None

```python
from returns.maybe import Maybe, Some, Nothing

def lookup_tag(self, name: str) -> Maybe[Tag]:
    if name in self._tags:
        return Some(self._tags[name])
    return Nothing
```

### Typed errors (not strings)

```python
from dataclasses import dataclass

@dataclass
class LintError:
    code: str
    message: str
    location: Location | None = None

# Usage in Result:
# Result[SymbolTable, LintError]
# Result[ParsedRung, LintError]
# But checks return list[Diagnostic] — they can't "fail", they produce results
```

### Checks return list[Diagnostic], not Result

A check always "succeeds" — it might just produce zero diagnostics. Only fallible operations (parsing, tag resolution) return `Result`.

```python
def check_undefined_tags(routine: Routine, scope: SymbolTable) -> list[Diagnostic]:
    return [
        Diagnostic("E001", f"Undefined tag '{ref}'", loc)
        for ref in extract_tag_refs(routine)
        if scope.lookup(ref) is Nothing
    ]
```

---

## Rules

1. **No bare exceptions** — use `@safe` decorator from `returns` to convert exceptions to `Result`.
2. **No None** — use `Maybe`, pattern-match with `case Some(val)` / `case Nothing`.
3. **No side effects in checks** — checks are pure: same input → same output.
4. **Adapter is the only impure layer** — it reads files, calls l5x library. Everything else is pure.
5. **One file per check** — makes tests trivial: pass a broken L5X, assert exact diagnostics.
