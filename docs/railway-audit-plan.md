# Railway Programming Audit & Enforcement Plan

## Current State: Two Error Categories Conflated

```
errors.py (E001-W005) ──► User-facing diagnostic codes (linter OUTPUT)
                           Used in checks/ to build Diagnostic objects
                           TYPE: never used in any Result annotation

NO EQUIVALENT             ◄── Internal railway errors (linter PLUMBING)
                           Currently: raw Exception / UnexpectedInput everywhere
                           All 4 Result annotations use Exception as type param
```

## Phase 1: Consolidate `domain/errors.py` into `checks/`

**Move** user-facing error codes (E001-W005) from `domain/errors.py` into `checks/` since they belong to the check implementations, not the domain core.

```
Before:                     After:
domain/errors.py            domain/errors.py  (deleted)
checks/e001_*.py            checks/_codes.py  (single file, all E/W codes)
checks/e001_*.py ──import──► checks._codes
```

Each check imports its code from `checks._codes` instead of `domain.errors`:

```python
# Before
from l5x_lint.domain.errors import E001

# After
from l5x_lint.checks._codes import E001
```

**Why:** These codes are only ever consumed by checks to stamp `Diagnostic` objects. They're not domain infrastructure — they're check-specific constants.

## Phase 2: Create `domain/errors.py` — Internal Railway Errors

New file with a typed union of internal pipeline errors:

```python
# domain/errors.py — Internal railway errors (linter PLUMBING)

@dataclass
class L5XStructureError:
    """Missing expected XML element or malformed structure."""
    element: str
    detail: str

@dataclass
class RLLParseError:
    """RLL grammar could not parse the rung text."""
    text: str
    position: int | None = None

@dataclass
class STParseError:
    """ST grammar could not parse the routine text."""
    text: str
    position: int | None = None

@dataclass
class UnsupportedRoutineError:
    """Routine type is not supported (FBD, SFC, etc.)."""
    routine_name: str
    routine_type: str

@dataclass
class SymbolTableError:
    """Failed to build symbol table."""
    detail: str

@dataclass
class AdapterArgumentError:
    """Invalid argument to adapter (not str or Path)."""
    got: str

@dataclass
class SoftwareRevisionError:
    """Unrecognized or unparseable SoftwareRevision."""
    revision: str

LintInternalError = (
    L5XStructureError | RLLParseError | STParseError
    | UnsupportedRoutineError | SymbolTableError
    | AdapterArgumentError | SoftwareRevisionError
)
```

## Phase 3: Fix All 4 `Result` Annotations to Use `LintInternalError`

| File | Line | Before | After |
|---|---|---|---|
| `pipeline/st_parser.py` | 500 | `Result[StProgram, Exception]` | `Result[StProgram, LintInternalError]` |
| `pipeline/rung_parser.py` | 167 | `Result[list[ParsedRung], Exception]` | `Result[list[ParsedRung], LintInternalError]` |
| `pipeline/routine_router.py` | 9 | `Result[Controller, Exception]` | `Result[Controller, LintInternalError]` |
| `pipeline/analyze.py` | 20 | `Result[AnalysisResult, Exception]` | `Result[AnalysisResult, LintInternalError]` |

### Exception leak fixes per file:

**`pipeline/rung_parser.py:179-180`** — Replace raw `Failure(e)` with domain error:
```python
except UnexpectedInput as e:
    return Failure(RLLParseError(text=text, position=e.pos_in_stream))
```

**`pipeline/st_parser.py:507-508`** — Same pattern:
```python
except UnexpectedInput as e:
    return Failure(STParseError(text=text, position=e.pos_in_stream))
```

**`infrastructure/adapter.py:28`** — Replace `raise TypeError(...)` with domain error:
```python
# Remove @safe, return Result directly
def parse_l5x(source: str | Path) -> Result[L5XProject, LintInternalError]:
    ...
    if not isinstance(source, (str, Path)):
        return Failure(AdapterArgumentError(got=type(source).__name__))
```

**`infrastructure/adapter.py:35`** — Same pattern:
```python
if controller_el is None:
    return Failure(L5XStructureError(element="Controller", detail="Not found in L5X root"))
```

**`infrastructure/parsers/_factory.py:21-22`** — Replace silent `pass` with domain error:
```python
try:
    major = int(software_revision.split(".")[0])
except (ValueError, IndexError):
    return Failure(SoftwareRevisionError(revision=software_revision))
```
This requires `create_parser()` to return `Result[BaseParser, LintInternalError]`.

**Transformer method risk** — `st_parser.py` / `rung_parser.py` Lark transformer methods run inside `_parser.parse(text)` but outside the `except UnexpectedInput` block. A bug in a transformer (e.g., `TypeError` in `__init__`) propagates uncaught. Fix: wrap the Lark parse call more broadly or make transformers return `Result` themselves.

## Phase 4: Eliminate `.value_or(None)` — Use Proper Maybe Pattern

**9 call sites** across 5 check files convert `Maybe[Tag]` → `Tag | None`, defeating the purpose:

| File | Line |
|---|---|
| `checks/e001_undefined_tag.py` | 56, 167 |
| `checks/e002_type_mismatch.py` | 33, 69 |
| `checks/e005_invalid_member.py` | 46, 96 |
| `checks/e006_array_bounds.py` | 46, 92 |
| `checks/w004_timer_pre.py` | 26 |

**Before:**
```python
resolved = symbols.resolve(name, loc.program).value_or(None)
if resolved is None:
    result.append(...)
```

**After:**
```python
match symbols.resolve(name, loc.program):
    case Nothing:
        result.append(...)
    case Some(tag):
        ...  # use tag
```

## Phase 5: Introduce `flow` + `bind` in Pipeline

Replace imperative `match/case` passthrough with functional composition:

**`pipeline/analyze.py` — Before:**
```python
def analyze(controller: Controller) -> Result[AnalysisResult, Exception]:
    route_result = route_routines(controller)
    match route_result:
        case Failure(err):
            return Failure(err)
        case Success():
            pass
    symbols = build_symbol_table(controller)
    diagnostics = ...
    ...
```

**After:**
```python
from returns.pipeline import flow
from returns.pointfree import bind

def analyze(controller: Controller) -> Result[AnalysisResult, LintInternalError]:
    return flow(
        controller,
        bind(route_routines),
        bind(_run_checks),
    )

def _run_checks(controller: Controller) -> Result[AnalysisResult, LintInternalError]:
    symbols = build_symbol_table(controller)
    diagnostics = ...
    ...
```

**`pipeline/routine_router.py` — Before:**
```python
match result:
    case Success(value): ...
    case Failure(): return Failure(result.failure)
```

**After:**
```python
# Replace with .map() / .alt() / .rescue() combinators
return result.map(...).alt(lambda e: Failure(...))
```

## Phase 6: Add Error Boundary Around Checks

Currently `analyze.py:35` calls each check directly — an unexpected exception in any check crashes the entire linter:

```python
for check in _registry:
    diagnostics.extend(check(r, symbols, loc))  # NO BOUNDARY
```

Wrap each check call to capture unexpected failures as `LintInternalError`:

```python
for check in _registry:
    try:
        diagnostics.extend(check(r, symbols, loc))
    except Exception as e:
        return Failure(CheckExecutionError(check=check.__name__, detail=str(e)))
```

This ensures one buggy check doesn't take down the whole analysis.

## Summary of New/Changed Files

| File | Action |
|---|---|
| `domain/errors.py` | **Rewrite** — replace E001-W005 with `LintInternalError` union |
| `checks/_codes.py` | **Create** — move E001-W005 here from old `domain/errors.py` |
| `checks/e001_undefined_tag.py` | Update import to `checks._codes`, replace `.value_or(None)` with `match .. case Some/Nothing` |
| `checks/e002_type_mismatch.py` | Same as above |
| `checks/e005_invalid_member.py` | Same as above |
| `checks/e006_array_bounds.py` | Same as above |
| `checks/w004_timer_pre.py` | Same as above |
| `pipeline/rung_parser.py` | Return `Result[list[ParsedRung], LintInternalError]`, wrap exception in `RLLParseError` |
| `pipeline/st_parser.py` | Return `Result[StProgram, LintInternalError]`, wrap exception in `STParseError` |
| `pipeline/routine_router.py` | Return `Result[Controller, LintInternalError]`, use `.map()`/`.alt()` instead of `match` |
| `pipeline/analyze.py` | Return `Result[AnalysisResult, LintInternalError]`, use `flow`+`bind`, add check error boundary |
| `infrastructure/adapter.py` | Return `Result[L5XProject, LintInternalError]` directly, remove `@safe` |
| `infrastructure/parsers/_factory.py` | Return `Result[BaseParser, LintInternalError]`, report bad revisions |
| `presentation/cli.py` | Update `match` arms for new error type |
| `presentation/mcp_server.py` | Update `match` arms for new error type, fix unguarded `raise ImportError` |
| `domain/errors.py` (existing tests) | Update to test `LintInternalError` instead of E001-W005 |
| `tests/checks/test_e001*.py` | Update imports |

## Phase 7: Update AGENTS.md — Railway Enforcement Rules

Replace the current "Functional Patterns" section in `AGENTS.md` with enforceable rules that future agents must follow:

### Current AGENTS.md (lines 39-62) — too permissive:
```python
# Shows @safe, flow, bind as "examples" — no rules, no enforcement
```

### Replacement content:

````markdown
## Railway Programming Rules (MUST FOLLOW)

All code in this repo MUST follow railway-oriented programming via the `returns` library.

### Rule 1: `Result` error type MUST be `LintInternalError`

```python
# ✅ CORRECT
from returns.result import Result, Success, Failure
from l5x_lint.domain.errors import LintInternalError

def parse(text: str) -> Result[StProgram, LintInternalError]:
    ...

# ❌ WRONG — never use raw Exception as error param
def parse(text: str) -> Result[StProgram, Exception]:
    ...
```

### Rule 2: Never `.value_or(None)` on a `Maybe`

```python
# ✅ CORRECT — pattern match on Maybe
match symbols.resolve(name, prog):
    case Nothing:
        return Failure(...)
    case Some(tag):
        ...

# ❌ WRONG — defeats the purpose of Maybe
tag = symbols.resolve(name, prog).value_or(None)
if tag is None:
    ...
```

### Rule 3: Prefer `flow` + `bind` over manual `match` passthrough

```python
# ✅ CORRECT — functional composition
from returns.pipeline import flow
from returns.pointfree import bind

def analyze(c: Controller) -> Result[AnalysisResult, LintInternalError]:
    return flow(c, bind(route_routines), bind(_run_checks))

# ❌ WRONG — manual match/case passthrough
result = route_routines(c)
match result:
    case Failure(err): return Failure(err)
    case Success(): pass
```

### Rule 4: `Failure` MUST wrap a domain error, not a raw exception

```python
# ✅ CORRECT
from l5x_lint.domain.errors import RLLParseError
except UnexpectedInput as e:
    return Failure(RLLParseError(text=text, position=e.pos_in_stream))

# ❌ WRONG — leaks raw library exception
except UnexpectedInput as e:
    return Failure(e)
```

### Rule 5: Every `try` block in a `Result`-returning function MUST map exceptions to domain errors

```python
# ✅ CORRECT
try:
    result = _parser.parse(text)
    return Success(result)
except UnexpectedInput as e:
    return Failure(STParseError(text=text, position=e.pos_in_stream))

# ❌ WRONG — generic catch
except Exception as e:
    return Failure(e)
```
````

## Migration Order

```
Phase 1 ──► checks/_codes.py  ──► Update all 15 check imports
                                      (no behavior change, pure rename)

Phase 2 ──► domain/errors.py   ──► LintInternalError union

Phase 3 ──► Fix Result types in pipeline, adapter, parsers
              rung_parser/st_parser/routine_router/analyze/adapter/_factory

Phase 4 ──► Replace .value_or(None) with match Some/Nothing in 5 check files

Phase 5 ──► Introduce flow + bind in pipeline

Phase 6 ──► Add error boundary around check execution

Phase 7 ──► Update AGENTS.md with 5 railway rules above
```
