# Project Structure

## Test Folder Mirrors Source

Every module in `src/l5x_lint/` has a corresponding test file at the same relative path under `tests/`.

```
src/l5x_lint/domain/models.py         →  tests/domain/test_models.py
src/l5x_lint/domain/diagnostics.py    →  tests/domain/test_diagnostics.py
src/l5x_lint/domain/errors.py         →  tests/domain/test_errors.py
src/l5x_lint/checks/e001_foo.py       →  tests/checks/test_e001_foo.py
```

# Toolchain

## uv (Package Management)

```powershell
uv sync                           # Install all deps from pyproject.toml
uv add <package>                  # Add runtime dependency
uv add --dev <package>            # Add dev dependency
uv run python -m l5x_lint ...    # Run module in env
uv run pytest tests/ -v          # Run tests
uv run pytest tests/ --cov       # Run with coverage
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

## Functional Patterns (returns library)

```python
from returns.result import Result, Success, Failure, safe
from returns.maybe import Maybe, Some, Nothing
from returns.pipeline import flow
from returns.pointfree import bind

# Result for fallible operations
def resolve(name: str) -> Result[Tag, LintError]:
    match self.lookup(name):
        case Nothing: return Failure(LintError(...))
        case Some(tag): return Success(tag)

# flow for linear pipelines
result = flow(input, step1, bind(step2), bind(step3))

# @safe converts exceptions → Failure automatically
@safe
def parse(xml: str) -> L5XProject: ...

# Maybe instead of None
def lookup(self, name: str) -> Maybe[Tag]: ...
```
