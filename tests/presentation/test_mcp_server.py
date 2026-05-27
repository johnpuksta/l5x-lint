import json
from pathlib import Path

import pytest

from l5x_lint.domain.diagnostics import Diagnostic
from l5x_lint.pipeline import analyze
from l5x_lint.presentation.mcp_server import _validate, create_server

TEST_DATA = Path(__file__).parent.parent / "data"
VALID_DIR = TEST_DATA / "valid"
INVALID_DIR = TEST_DATA / "invalid"


def _register_demo_check():
    analyze._registry.clear()

    def _demo_check(routine, symbols, location):
        return [
            Diagnostic(
                code="DEMO", severity="warning", location=location, message="test",
            ),
        ]

    analyze.register(_demo_check)


def test_validate_valid_file():
    result = json.loads(_validate(VALID_DIR / "projects" / "Simple.L5X"))
    assert "passed" in result
    assert "error_count" in result
    assert "warning_count" in result
    assert "diagnostics" in result


def test_validate_json_structure():
    result = json.loads(_validate(VALID_DIR / "projects" / "Simple.L5X"))
    assert "diagnostics" in result
    assert "passed" in result
    assert "error_count" in result
    assert "warning_count" in result
    assert isinstance(result["diagnostics"], list)


def test_validate_nonexistent_file():
    result = json.loads(_validate(Path("nonexistent.L5X")))
    assert "error" in result
    assert "passed" not in result


def test_validate_with_diagnostics():
    _register_demo_check()
    result = json.loads(_validate(VALID_DIR / "projects" / "Simple.L5X"))
    assert result["passed"] is True
    assert result["error_count"] == 0
    assert result["warning_count"] > 0
    assert len(result["diagnostics"]) > 0


@pytest.mark.anyio
async def test_mcp_tool_is_listed():
    server = create_server()
    tools = await server.list_tools()
    names = [t.name for t in tools]
    assert "validate_l5x" in names
