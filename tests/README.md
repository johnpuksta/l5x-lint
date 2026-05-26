# Test Structure

```
tests/
  conftest.py                # Shared fixtures
  test_data_inventory.py     # Validates test data integrity
  data/
    valid/                   # Working L5X files (parsing must succeed)
      projects/              # Full controller exports
      routines/              # Individual routine exports
      rungs/                 # Individual rung exports
      datatypes/             # Data type definition exports
      instructions/          # AOI definition exports
    invalid/                 # Intentionally broken L5X files
      E001_*.L5X             # Undefined tag reference
      E002_*.L5X             # Type mismatch
      E003_*.L5X             # Missing AOI definition
      E004_*.L5X             # Invalid JSR target
      E005_*.L5X             # Invalid UDT member access
      E006_*.L5X             # Array index out of bounds
      E007_*.L5X             # Duplicate tag name
      E009_*.L5X             # Wrong operand count
      E010_*.L5X             # Cross-scope tag violation
      W001_*.L5X             # Unused tag declared
      W002_*.L5X             # Unreachable rung
      W003_*.L5X             # Output never driven
      W004_*.L5X             # Timer PRE never set
      W005_*.L5X             # Shadowed tag name
```

## Running Tests

```bash
pytest tests/ -v
```

## Adding Tests

1. Add a valid `.L5X` file under `data/valid/`
2. Add a broken `.L5X` under `data/invalid/` with prefix `EXXX_` or `WXXX_`
3. Write a test that calls `analyze_l5x(file)` and asserts the expected diagnostic codes
