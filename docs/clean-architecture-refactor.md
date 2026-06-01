# Clean Architecture Refactor Plan

## 1. Problem Statement

The current codebase has a `pipeline/` module that conflates three distinct concerns:

- **Application orchestration** (`analyze.py`, `config.py`, `filter.py`, `routine_router.py`)
- **Infrastructure adapters** (`rung_parser.py`, `st_parser.py` — depend on `lark`)
- **Domain concepts** (`dialect.py`, `symbols.py` — pure business logic with no external deps)

Additionally:

- `checks/` (business rules) sits at the top level instead of inside `domain/`
- `schemas/` (XSD data files) lives inside the Python package source tree
- `pipeline/dialect.py` has global mutable state (`_current_dialect`) that is set but never consumed by any check (dead code)
- The package is double-nested: `src/l5x_lint/` — the `l5x_lint` subfolder inside `src/` is unnecessary

## 2. Target Architecture

After the refactor, the package root will be `src/` directly (no `l5x_lint` subfolder).

```
src/
├── __init__.py
├── __main__.py
│
├── domain/                        # PURE — no external deps
│   ├── __init__.py
│   ├── models.py                  # (unchanged)
│   ├── rll_models.py              # (unchanged)
│   ├── st_models.py               # (unchanged)
│   ├── diagnostics.py             # (unchanged)
│   ├── errors.py                  # (unchanged)
│   ├── dialect.py                 # ← MOVED from pipeline/ (DialectConfig, presets)
│   ├── symbols.py                 # ← MOVED from pipeline/ (SymbolTable, build_symbol_table)
│   └── checks/                    # ← MOVED from top-level checks/
│       ├── __init__.py
│       ├── _codes.py
│       ├── _hints.py
│       ├── _types.py
│       ├── _walkers.py
│       ├── opcodes.py
│       ├── tag_refs.py
│       ├── cross/                 # (all check files unchanged internally)
│       ├── rll/                   # (all check files unchanged internally)
│       └── st/                    # (all check files unchanged internally)
│
├── application/                   # NEW — use cases, orchestration
│   ├── __init__.py
│   ├── analyze.py                 # ← MOVED from pipeline/ (analyze(), register(), _run_checks)
│   ├── config.py                  # ← MOVED from pipeline/ (LintConfig, apply_warning_toggles)
│   ├── filter.py                  # ← MOVED from pipeline/ (filter_diagnostics)
│   └── routine_router.py          # ← MOVED from pipeline/ (route_routines)
│
├── infrastructure/                # TECHNICAL IMPLEMENTATIONS
│   ├── __init__.py
│   ├── adapter.py                 # (unchanged — parse_l5x entry point)
│   ├── _xsd.py                    # (path update for schemas/)
│   ├── rung_parser.py             # ← MOVED from pipeline/ (Lark RLL parser)
│   ├── st_parser.py               # ← MOVED from pipeline/ (Lark ST parser)
│   └── xml_parsers/               # ← RENAMED from parsers/ (L5X XML parsers)
│       ├── __init__.py
│       ├── _factory.py
│       ├── base.py
│       └── v38.py
│
├── presentation/                  # (unchanged)
│   ├── __init__.py
│   ├── cli.py
│   ├── mcp_server.py
│   └── _format.py
│
└── schemas/                       # ← MOVED from src/l5x_lint/schemas/ to project root
    ├── l5x-v32.xsd
    ├── l5x-v33.xsd
    ├── l5x-v34.xsd
    ├── l5x-v35.xsd
    ├── l5x-v36.xsd
    ├── l5x-v37.xsd
    └── l5x-v38.xsd
```

### Dependency Direction

```
presentation/ → application/ → domain/
                  ↓               ↑
            infrastructure/ ─────┘
```

- `domain/` imports nothing outside stdlib (pure Python dataclasses)
- `application/` imports from `domain/` only
- `infrastructure/` imports from `domain/` (parsing into domain models)
- `presentation/` imports from `application/` and `infrastructure/` (wires everything together)

## 3. Import Remapping Reference

### Old → New import paths

`src/` is the source root (not a package). Imports drop the `l5x_lint` namespace entirely.

| Old import | New import |
|------------|------------|
| `from l5x_lint.pipeline.dialect import ...` | `from domain.dialect import ...` |
| `from l5x_lint.pipeline.symbols import ...` | `from domain.symbols import ...` |
| `from l5x_lint.pipeline.analyze import ...` | `from application.analyze import ...` |
| `from l5x_lint.pipeline.config import ...` | `from application.config import ...` |
| `from l5x_lint.pipeline.filter import ...` | `from application.filter import ...` |
| `from l5x_lint.pipeline.routine_router import ...` | `from application.routine_router import ...` |
| `from l5x_lint.pipeline.rung_parser import ...` | `from infrastructure.rung_parser import ...` |
| `from l5x_lint.pipeline.st_parser import ...` | `from infrastructure.st_parser import ...` |
| `from l5x_lint.checks import ...` | `from domain.checks import ...` |
| `from l5x_lint.checks.cross import ...` | `from domain.checks.cross import ...` |
| `from l5x_lint.checks.rll import ...` | `from domain.checks.rll import ...` |
| `from l5x_lint.checks.st import ...` | `from domain.checks.st import ...` |
| `from l5x_lint.checks._codes import ...` | `from domain.checks._codes import ...` |
| `from l5x_lint.checks._walkers import ...` | `from domain.checks._walkers import ...` |
| `from l5x_lint.checks._types import ...` | `from domain.checks._types import ...` |
| `from l5x_lint.checks._hints import ...` | `from domain.checks._hints import ...` |
| `from l5x_lint.infrastructure.adapter import ...` | `from infrastructure.adapter import ...` |
| `from l5x_lint.infrastructure.parsers import ...` | `from infrastructure.xml_parsers import ...` |
| `from l5x_lint.infrastructure.parsers.base import ...` | `from infrastructure.xml_parsers.base import ...` |
| `from l5x_lint.infrastructure.parsers.v38 import ...` | `from infrastructure.xml_parsers.v38 import ...` |
| `from l5x_lint.infrastructure.parsers._factory import ...` | `from infrastructure.xml_parsers._factory import ...` |
| `from l5x_lint.domain import ...` | `from domain import ...` |
| `from l5x_lint.presentation.cli import ...` | `from presentation.cli import ...` |
| `from l5x_lint.presentation.mcp_server import ...` | `from presentation.mcp_server import ...` |
| `from l5x_lint.presentation._format import ...` | `from presentation._format import ...` |

## 4. Step-by-Step Execution Plan

### Step 0: Remove double-nested package

**Goal:** Eliminate `src/l5x_lint/` — promote its contents to `src/` directly.

**Actions:**
1. Move all contents of `src/l5x_lint/` up to `src/`
2. Remove the now-empty `src/l5x_lint/` directory
3. Update `pyproject.toml`:
   ```toml
   [tool.setuptools.packages.find]
   where = ["src"]
   include = ["domain*", "application*", "infrastructure*", "presentation*"]
   
   [project.scripts]
   l5x-lint = "presentation.cli:main"
   l5x-lint-mcp = "presentation.mcp_server:main"
   ```
4. Update `src/__main__.py`:
   ```python
   from presentation.cli import main
   main()
   ```
5. Update every `from l5x_lint.` import to drop the `l5x_lint.` prefix throughout the codebase (e.g., `from l5x_lint.domain.models import ...` → `from domain.models import ...`)

**Verification:** `uv run pytest tests/ -v` — all tests pass

**Files affected:** Every `.py` file in `src/` and `tests/` (import path changes)

---

### Step 1: Move domain concepts out of pipeline/ ✅ DONE

**Goal:** `dialect.py` and `symbols.py` belong in `domain/`, not `pipeline/`.

**Actions:**
1. Move `pipeline/dialect.py` → `domain/dialect.py`
2. Move `pipeline/symbols.py` → `domain/symbols.py`
3. Update imports in:
   - `application/analyze.py` (was `pipeline/analyze.py`): `from domain.dialect import ...`, `from domain.symbols import ...`
   - `application/routine_router.py` (was `pipeline/routine_router.py`): no change needed (doesn't import dialect/symbols directly)
   - `domain/checks/_walkers.py`: `from domain.symbols import SymbolTable`
   - `domain/checks/_types.py`: `from domain.symbols import BUILTIN_TYPES, SymbolTable`
   - Every check file that imports `SymbolTable` from `pipeline.symbols` → `domain.symbols`

**Verification:** `uv run pytest tests/ -v`

**Files affected:**
- `src/domain/dialect.py` (moved)
- `src/domain/symbols.py` (moved)
- `src/application/analyze.py` (import update)
- `src/domain/checks/_walkers.py` (import update)
- `src/domain/checks/_types.py` (import update)
- ~40 check files (import update: `pipeline.symbols` → `domain.symbols`)
- `tests/pipeline/test_dialect.py` → `tests/domain/test_dialect.py`
- `tests/pipeline/test_symbols.py` → `tests/domain/test_symbols.py`

---

### Step 2: Move checks into domain/

**Goal:** Checks are business rules — they belong in `domain/checks/`.

**Actions:**
1. Move `checks/` → `domain/checks/`
2. Update every check file's import of `register`:
   - `from application.analyze import register` (was `from l5x_lint.pipeline.analyze import register`)
3. Update `domain/checks/__init__.py` to import sub-packages correctly
4. Update `presentation/cli.py`: `import domain.checks` (was `import l5x_lint.checks`)
5. Update `presentation/mcp_server.py`: same pattern
6. Update `tests/test_integration.py`: `_reset_all_check_state()` references

**Verification:** `uv run pytest tests/ -v`

**Files affected:**
- `src/domain/checks/` (entire directory moved)
- `src/domain/checks/cross/*.py` (~18 files — import update)
- `src/domain/checks/rll/*.py` (~13 files — import update)
- `src/domain/checks/st/*.py` (~17 files — import update)
- `src/domain/checks/_walkers.py` (import update)
- `src/domain/checks/_types.py` (import update)
- `src/presentation/cli.py` (import update)
- `src/presentation/mcp_server.py` (import update)
- `tests/test_integration.py` (import update)
- `tests/checks/` → `tests/domain/checks/`

---

### Step 3: Create application layer

**Goal:** Explicit application layer with use cases and orchestration.

**Actions:**
1. Create `application/` directory with `__init__.py`
2. Move files:
   - `pipeline/analyze.py` → `application/analyze.py`
   - `pipeline/config.py` → `application/config.py`
   - `pipeline/filter.py` → `application/filter.py`
   - `pipeline/routine_router.py` → `application/routine_router.py`
3. Update imports inside moved files:
   - `application/analyze.py`:
     - `from domain.dialect import resolve_dialect` (was `pipeline.dialect`)
     - Remove `set_dialect` import (dead code — see step 6)
     - `from domain.symbols import SymbolTable, build_symbol_table` (was `pipeline.symbols`)
     - `from application.config import LintConfig` (was `pipeline.config`)
     - `from application.filter import filter_diagnostics` (was `pipeline.filter`)
     - `from application.routine_router import route_routines` (was `pipeline.routine_router`)
   - `application/filter.py`:
     - `from application.config import LintConfig` (was `pipeline.config`)
   - `application/routine_router.py`:
     - `from infrastructure import rung_parser, st_parser` (was `from l5x_lint.pipeline import ...`)
4. Update presentation imports:
   - `cli.py`: `from application.analyze import analyze`, `from application.config import ...`
   - `mcp_server.py`: same pattern
5. Update `tests/test_integration.py`: `from application import analyze as analyze_module`

**Verification:** `uv run pytest tests/ -v`

**Files affected:**
- `src/application/__init__.py` (new)
- `src/application/analyze.py` (moved)
- `src/application/config.py` (moved)
- `src/application/filter.py` (moved)
- `src/application/routine_router.py` (moved)
- `src/presentation/cli.py` (import update)
- `src/presentation/mcp_server.py` (import update)
- `tests/test_integration.py` (import update)
- `tests/pipeline/test_analyze.py` → `tests/application/test_analyze.py`
- `tests/pipeline/test_config.py` → `tests/application/test_config.py`
- `tests/pipeline/test_filter.py` → `tests/application/test_filter.py`
- `tests/pipeline/test_routine_router.py` → `tests/application/test_routine_router.py`

---

### Step 4: Move parsers into infrastructure/ + rename parsers/ to xml_parsers/

**Goal:** Lark-dependent parsers are infrastructure adapters. Rename `parsers/` to `xml_parsers/` to distinguish XML parsers from text parsers.

**Actions:**
1. Move `pipeline/rung_parser.py` → `infrastructure/rung_parser.py`
2. Move `pipeline/st_parser.py` → `infrastructure/st_parser.py`
3. Rename `infrastructure/parsers/` → `infrastructure/xml_parsers/`
4. Update `application/routine_router.py`:
   - `from infrastructure import rung_parser, st_parser` (was `from l5x_lint.pipeline import ...`)
5. Update XML parser internal imports (`infrastructure.xml_parsers` replaces `infrastructure.parsers`):
   - `infrastructure/adapter.py`: `from infrastructure.xml_parsers._factory import create_parser`
   - `infrastructure/xml_parsers/_factory.py`: `from infrastructure.xml_parsers.base import ...`
   - `infrastructure/xml_parsers/v38.py`: `from infrastructure.xml_parsers.base import L5XParser`
6. Update tests:
   - `tests/pipeline/test_rung_parser.py` → `tests/infrastructure/test_rung_parser.py`
   - `tests/pipeline/test_st_parser.py` → `tests/infrastructure/test_st_parser.py`
   - `tests/infrastructure/test_adapter.py`: update `xml_parsers` imports

**Verification:** `uv run pytest tests/ -v`

**Files affected:**
- `src/infrastructure/rung_parser.py` (moved)
- `src/infrastructure/st_parser.py` (moved)
- `src/infrastructure/xml_parsers/` (renamed from parsers/)
- `src/infrastructure/adapter.py` (import update)
- `src/infrastructure/xml_parsers/_factory.py` (import update)
- `src/infrastructure/xml_parsers/v38.py` (import update)
- `src/application/routine_router.py` (import update)
- `tests/infrastructure/test_rung_parser.py` (moved)
- `tests/infrastructure/test_st_parser.py` (moved)
- `tests/infrastructure/test_adapter.py` (import update)

---

### Step 5: Move schemas/ to project root

**Goal:** Static XSD data files don't belong in the Python package source tree.

**Actions:**
1. Move `src/schemas/` → `schemas/` (project root, alongside `references/`)
2. Update `infrastructure/_xsd.py`:
   ```python
   # Old:
   _SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
   # New:
   _SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"
   ```
3. Update `pyproject.toml` if needed (exclude `schemas/` from package data)
4. Update `.gitignore` if schemas were tracked differently

**Verification:** `uv run pytest tests/ -v`

**Files affected:**
- `schemas/` (moved to project root)
- `src/infrastructure/_xsd.py` (path update)

---

### Step 6: Remove dead global dialect state

**Goal:** The `_current_dialect` global in `dialect.py` is set by `analyze()` but never read by any check. Remove it.

**Current state (confirmed by grep):**
- `set_dialect()` is called in `application/analyze.py` line 35
- `get_dialect()` is imported only in `tests/pipeline/test_dialect.py`
- **No check file imports or calls `get_dialect()`** — the global is dead code

**Actions:**
1. In `domain/dialect.py`:
   - Remove `_current_dialect` global variable
   - Remove `get_dialect()` function
   - Remove `set_dialect()` function
   - Keep: `DialectConfig`, `DIALECT_PRESETS`, `resolve_dialect()`
2. In `application/analyze.py`:
   - Remove `set_dialect` import
   - Remove `set_dialect(resolve_dialect(config.dialect))` call (line 35)
   - The dialect info stays in `config.dialect` (a string) for future use
3. In `tests/domain/test_dialect.py` (was `tests/pipeline/test_dialect.py`):
   - Remove tests for `get_dialect()` / `set_dialect()`
   - Keep tests for `DialectConfig`, `DIALECT_PRESETS`, `resolve_dialect()`

**Verification:** `uv run pytest tests/ -v`

**Files affected:**
- `src/domain/dialect.py` (remove 3 items)
- `src/application/analyze.py` (remove 2 lines)
- `tests/domain/test_dialect.py` (remove 2 test functions)

---

### Step 7: Delete pipeline/

**Goal:** The `pipeline/` module is now empty — delete it.

**Actions:**
1. Delete `pipeline/` directory entirely (all contents were moved in steps 1-4)

**Verification:** `uv run pytest tests/ -v && uvx ruff check .`

**Files affected:**
- `src/pipeline/` (deleted entirely)

---

### Step 8: Restructure test directory

**Goal:** Mirror the new source layout in tests.

**Target test structure:**
```
tests/
├── __init__.py
├── conftest.py
├── helpers.py
├── data/                          # (unchanged)
├── domain/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_diagnostics.py
│   ├── test_errors.py
│   ├── test_symbols.py            # ← from tests/pipeline/
│   ├── test_dialect.py            # ← from tests/pipeline/ (trimmed)
│   └── checks/                    # ← from tests/checks/
│       ├── __init__.py
│       ├── cross/
│       ├── rll/
│       ├── st/
│       ├── test_hints.py
│       └── test_walkers.py
├── application/
│   ├── __init__.py
│   ├── test_analyze.py            # ← from tests/pipeline/
│   ├── test_config.py             # ← from tests/pipeline/
│   ├── test_filter.py             # ← from tests/pipeline/
│   └── test_routine_router.py     # ← from tests/pipeline/
├── infrastructure/
│   ├── __init__.py
│   ├── test_adapter.py
│   ├── test_rung_parser.py        # ← from tests/pipeline/
│   ├── test_st_parser.py          # ← from tests/pipeline/
│   └── test_xsd.py
├── presentation/
│   ├── __init__.py
│   ├── test_cli.py
│   └── test_mcp_server.py
├── test_integration.py
└── test_data_inventory.py
```

**Actions:**
1. Move test files to match new source structure
2. Update all test imports to use new paths
3. Run full test suite

**Verification:** `uv run pytest tests/ -v && uvx ruff check .`

---

## 5. Risk Assessment

| Step | Risk | Mitigation |
|------|------|-----------|
| 0: Remove double-nesting | Medium — changes every import in codebase | Do first, run tests immediately |
| 1: Move dialect/symbols to domain | Low — straightforward file moves | Automated find/replace |
| 2: Move checks to domain | Medium — ~50 files need import updates | Automated find/replace |
| 3: Create application layer | Medium — new directory, 4 file moves | Test after each file |
| 4: Move parsers to infra | Low — 2 files, 1 import update | Direct move |
| 5: Move schemas/ | Low — 1 path change in `_xsd.py` | Test XSD validation |
| 6: Remove dead dialect state | Low — confirmed no consumers | grep verification |
| 7: Delete pipeline/ | Low — only after all moves verified | ruff check catches broken imports |
| 8: Restructure tests | Low — test-only changes | Full test suite run |

**Highest risk:** Step 0 (removing the `l5x_lint` subfolder) because it touches every import. Consider doing this as a dedicated commit before the architectural moves.

## 6. Verification Commands (run after each step)

```powershell
uv run pytest tests/ -v          # All tests pass
uvx ruff check .                 # No lint errors
uvx ruff format --check .        # Formatting intact
```

## 7. Execution Order Summary

| Step | Description | Files moved | Files updated |
|------|-------------|-------------|---------------|
| 0 | Remove double-nested package | ~15 files up one level | ~60 import updates |
| 1 | Move dialect/symbols to domain | 2 | ~45 |
| 2 | Move checks to domain | ~55 | ~55 |
| 3 | Create application layer | 4 | ~10 |
| 4 | Move parsers + rename parsers/ to xml_parsers/ | 2 moves + 1 rename | ~5 |
| 5 | Move schemas/ to project root | 7 XSD files | 1 |
| 6 | Remove dead dialect state | 0 (deletions) | 3 |
| 7 | Delete pipeline/ | 0 (deletion) | 0 |
| 8 | Restructure tests | ~15 | ~15 |
