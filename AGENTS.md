# Project Structure

```
src/
├── domain/           # Pure business logic (no external deps)
│   ├── checks/       # Check rules (ec*, wc*, ws*, er*, wr*, es*)
│   ├── dialect.py    # DialectConfig and presets
│   ├── symbols.py    # SymbolTable and resolution
│   └── models.py     # Core dataclasses
├── application/      # Use cases and orchestration
│   ├── analyze.py    # Main entry point, check registry
│   ├── config.py     # LintConfig
│   └── routine_router.py
├── infrastructure/   # External adapters
│   ├── adapter.py    # L5X XML parsing entry point
│   ├── xml_parsers/  # Lark-based parsers (RLL, ST)
│   └── _xsd.py       # XSD validation
└── presentation/     # CLI and MCP server
```

## Test Folder Mirrors Source

Every module in `src/` has a corresponding test file at the same relative path under `tests/unit/`.

## Adding a New Check

1. Create `src/domain/checks/<category>/<code>_<name>.py`
2. Use `StWalker` or `RllWalker` from `domain/checks/_walkers.py`
3. Call `register()` from `application.analyze`
4. Add test in `tests/unit/domain/checks/<category>/test_<code>_<name>.py`
5. Import in `src/domain/checks/<category>/__init__.py`

# Toolchain

## uv (Package Management)

```powershell
uv sync                           # Install all deps from pyproject.toml
uv add <package>                  # Add runtime dependency
uv add --dev <package>            # Add dev dependency
uv run python -m l5x_lint ...    # Run module in env
uv run pytest tests/unit tests/benchmarks -v          # Run tests
uv run pytest tests/unit tests/benchmarks --cov       # Run with coverage
uvx ruff check .                  # Lint with ruff (ephemeral)
```

## Ruff (Linting + Formatting)

```powershell
uvx ruff check .                  # Lint all files
uvx ruff check --fix .            # Auto-fix
uvx ruff format .                 # Format all files
uvx ruff format --check .         # Check formatting (CI)
```

Rules: `pyproject.toml` under `[tool.ruff]` if needed, defaults otherwise.

# Railway Programming Rules

```python
from returns.result import Result, Success, Failure
from returns.maybe import Maybe, Some, Nothing
from returns.pipeline import flow
from returns.pointfree import bind
from domain.errors import LintInternalError

# 1. Error param MUST be LintInternalError, never raw Exception
def resolve(name: str) -> Result[Tag, LintInternalError]: ...

# 2. Never .value_or(None) — match Some/Nothing instead
match symbols.resolve(name, prog):
    case Nothing: return Failure(...)
    case Some(tag): ...

# 3. Prefer flow + bind over manual match passthrough
def analyze(c) -> Result[AnalysisResult, LintInternalError]:
    return flow(Success(c), bind(route_routines), bind(_run_checks))

# 4. Failure MUST wrap a domain error, not the raw exception
except UnexpectedInput as e:
    return Failure(STParseError(text=text, position=e.pos_in_stream))

# 5. Every try in a Result-returning fn maps exceptions to domain errors
try:
    return Success(_parser.parse(text))
except UnexpectedInput as e:
    return Failure(STParseError(text=text, position=e.pos_in_stream))
```
