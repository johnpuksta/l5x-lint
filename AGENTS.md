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

# Known Issues

## Lark Scanner Priority

Lark's `BasicLexer._build_scanner()` sorts terminals by `(-priority, -max_width, -len(pattern.value), name)` ascending. Higher numeric `priority` in grammar (e.g., `NAME.100`) means the terminal matches first (because `-100 < 0`).

Both parsers (`rung_parser.py`, `st_parser.py`) use `ContextualLexer`. Tag-like terminals (`TAG_BASE`) use priority `-1` to sort **after** keywords (priority `0`) — otherwise `-max_width` tiebreaker puts unbounded TAG_BASE before fixed-length keywords like `IF`.

**ST parser keywords** use `/(?i:keyword)/` regex (case-insensitive, avoids `%ignore_case` bug). All 26 keyword terminals default to priority `0`. `TAG_BASE.-1` ensures identifiers don't shadow keywords.

**RLL parser** `TAG_BASE` uses two alternatives (IO tag format `Name:Slot:Letter` first, then simple identifier) with priority `0`. The IO colon pattern allows digits in first/last components: `[A-Za-z_][A-Za-z0-9_]*:[0-9]+:[A-Za-z_][A-Za-z0-9_]*`. `CMP.100` and `HEX_LITERAL.100` use high priority to match before broader `OPCODE`/`NUMBER` patterns.

## Inline String Literals in Alternatives

Lark drops inline string literal tokens (e.g., `"["`, `"]"`) from alternatives within `(...)*` groups. The `tag_path` rule in `rung_parser.py` uses `"[" NUMBER ("," NUMBER)* "]"` but the transformer receives only `TAG_BASE`, `NUMBER` tokens — brackets are invisible. Array indices are internally represented as `.N` (dot notation, same as structural member access) and tests assert `Array.5` not `Array[5]`. To preserve brackets, use named terminals (`LSQB: "["`, `RSQB: "]"`) in the grammar.

## Opcodes vs AOIs

E003 ("Missing AOI definition") uses a `_BUILTIN_OPCODES` frozenset in `e003_missing_aoi.py`. Any opcode not in this set and not defined as an AOI triggers E003. Both `_BUILTIN_OPCODES` and `OPCODE_OPERANDS` in `opcodes.py` must be kept in sync. `GT` was recently added as a comparison instruction alias alongside `GRT`.
