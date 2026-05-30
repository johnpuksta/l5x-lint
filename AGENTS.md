# Project Structure

## Test Folder Mirrors Source

Every module in `src/l5x_lint/` has a corresponding test file at the same relative path under `tests/`.

```
src/l5x_lint/domain/models.py             →  tests/domain/test_models.py
src/l5x_lint/domain/diagnostics.py        →  tests/domain/test_diagnostics.py
src/l5x_lint/domain/errors.py             →  tests/domain/test_errors.py  (internal railway errors)
src/l5x_lint/checks/_codes.py             →  tests/checks/cross/test_codes.py  (all diagnostic codes)
src/l5x_lint/checks/_types.py             →  (tested via checks that use it)
src/l5x_lint/checks/cross/ec*.py          →  tests/checks/cross/test_ec*.py  (15 cross error checks)
src/l5x_lint/checks/cross/wc*.py          →  tests/checks/cross/test_wc*.py  (4 cross warning checks)
src/l5x_lint/checks/cross/ws*.py          →  tests/checks/cross/test_ws*.py  (3 cross warning checks WS)
src/l5x_lint/checks/rll/er*.py            →  tests/checks/rll/test_er*.py  (3 rll error checks)
src/l5x_lint/checks/rll/wr*.py            →  tests/checks/rll/test_wr*.py  (6 rll warning checks)
src/l5x_lint/checks/st/ws*.py             →  tests/checks/st/test_ws*.py  (6 st warning checks)
src/l5x_lint/checks/st/es*.py             →  tests/checks/st/test_es*.py  (2 st error checks)
```

# Sub-Checker Walkers

Eliminates duplicated AST traversal (duplicated ~20× for RLL, ~6× for ST):

```python
from l5x_lint.checks._walkers import StWalker, RllWalker
from l5x_lint.pipeline.analyze import register

class MyCheck(StWalker):
    def visit_if(self, node):
        self.add_diagnostic("WSXXX", "warning", "missing else", line=node.line)

my_check = MyCheck()
register(my_check)
```

- **StWalker** — walks ST programs; override `visit_assignment`, `visit_if`, `visit_case`, `visit_for`, `visit_while`, `visit_repeat`, `visit_call`, `visit_jsr`, `visit_exit`, `visit_return`, `visit_binary_op`, `visit_unary_op`, `visit_tag_ref`, `visit_literal`
- **RllWalker** — walks RLL rungs/instructions (includes branch recursion); override `visit_rung(node)` / `visit_instruction(node)`; `self.rung_num` available
- `self.add_diagnostic(code, severity, message, line=..., rung=...)` convenience
- Both match `CheckFn` signature for `register(check_instance)`
- Default visit methods are no-ops; only override what you need

# Dialect System

Seven boolean flags on `DialectConfig` control check behavior across presets:

| Flag | rockwell | iec-61131-3 | codesys |
|---|---|---|---|
| `allow_keywords_case_insensitive` | True | False | False |
| `allow_positional_args` | True | False | True |
| `allow_jsr` | True | False | False |
| `allow_wildcard_operands` | True | False | True |
| `allow_type_punning` | True | False | True |
| `allow_c_style_comments` | True | False | True |
| `allow_cross_family_widening` | True | False | True |

Checks access the active dialect via a module-level session:

```python
from l5x_lint.pipeline.dialect import get_dialect

def visit_something(self, node):
    if get_dialect().allow_jsr:
        return  # JSR is normal in Rockwell; skip check
    ...
```

The session dialect is set by `analyze()` before running checks (`set_dialect(resolve_dialect(config.dialect))`). Import the module-level `get_dialect()` / `set_dialect()` from `pipeline/dialect.py`.

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

## Railway Programming Rules

```python
from returns.result import Result, Success, Failure
from returns.maybe import Maybe, Some, Nothing
from returns.pipeline import flow
from returns.pointfree import bind
from l5x_lint.domain.errors import LintInternalError

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
