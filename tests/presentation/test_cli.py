import json
from pathlib import Path

from l5x_lint.presentation.cli import validate

TEST_DATA = Path(__file__).parent.parent / "data"
VALID_DIR = TEST_DATA / "valid"


def test_validate_valid_file():
    rc = validate(VALID_DIR / "projects" / "Simple.L5X")
    assert rc == 0


def test_validate_valid_file_json():
    rc = validate(VALID_DIR / "projects" / "Simple.L5X", json_output=True)
    assert rc == 0


def test_validate_nonexistent_file():
    rc = validate(Path("nonexistent.L5X"))
    assert rc == 1


def test_validate_json_structure(capsys):
    validate(VALID_DIR / "projects" / "Simple.L5X", json_output=True)
    stdout = capsys.readouterr().out
    data = json.loads(stdout)
    assert "diagnostics" in data
    assert "passed" in data
    assert "error_count" in data
    assert "warning_count" in data
    assert data["passed"] is True


def test_validate_no_issues_output(capsys):
    validate(VALID_DIR / "projects" / "Simple.L5X")
    stdout = capsys.readouterr().out
    assert "No issues found." in stdout


def test_validate_invalid_xml():
    rc = validate(Path("this_file_does_not_exist.L5X"))
    assert rc == 1


def test_validate_parse_error_stderr(capsys):
    validate(Path("no_such_file.L5X"))
    stderr = capsys.readouterr().err
    assert "Error" in stderr
