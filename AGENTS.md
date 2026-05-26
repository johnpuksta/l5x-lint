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
