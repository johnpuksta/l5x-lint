"""End-to-end integration tests: parse L5X → run all checks → verify diagnostics."""

import sys
from pathlib import Path

import pytest
from returns.result import Success

from l5x_lint.infrastructure.adapter import parse_l5x
from l5x_lint.application import analyze as analyze_module
from l5x_lint.application.analyze import analyze


def _reset_all_check_state():
    """Reset the check registry and reload all check modules."""
    analyze_module._registry.clear()

    for mod_name in list(sys.modules):
        if (
            mod_name.startswith("l5x_lint.domain.checks.")
            and mod_name != "l5x_lint.domain.checks._codes"
        ):
            del sys.modules[mod_name]

    # Re-import all check packages to re-register
    import l5x_lint.domain.checks.cross  # noqa: F401
    import l5x_lint.domain.checks.rll  # noqa: F401
    import l5x_lint.domain.checks.st  # noqa: F401


INVALID_DIR = Path(__file__).parent / "data" / "invalid"

# (stem_prefix, expected_code(s)) for each invalid test data file
# Some files trigger multiple codes; we check at least the primary one.
INVALID_CASES = [
    ("EC001", "EC001"),
    ("EC002", "EC002"),
    ("EC003", "EC003"),
    ("EC004", "EC004"),
    ("EC005", "EC005"),
    ("EC006", "EC006"),
    ("EC007", "EC007"),
    ("EC010", "EC010"),
    ("EC011", "EC011"),
    ("EC012", "EC012"),
    ("EC013", "EC013"),
    ("EC014", "EC014"),
    ("EC015", "EC015"),
    ("EC016", "EC016"),
    ("EC017", "EC017"),
    ("EC018", "EC018"),
    ("WC001", "WC001"),
    ("WC005", "WC005"),
    ("WC103", "WC103"),
    ("WC106", "WC106"),
    ("WC107", "WC107"),
    ("WC108", "WC108"),
    ("WS101", "WS101"),
    ("WS102", "WS102"),
    ("WS104", "WS104"),
    ("WS105", "WS105"),
    ("WS107", "WS107"),
    ("WS108", "WS108"),
    ("WS109", "WS109"),
    ("WS110", "WS110"),
    ("WS111", "WS111"),
    ("WS112", "WS112"),
    ("WS113", "WS113"),
    ("WS114", "WS114"),
    ("WS115", "WS115"),
    ("WS117", "WS117"),
    ("WS118", "WS118"),
    ("ER009", "ER009"),
    ("ER013", "ER013"),
    ("ER014", "ER014"),
    ("ER015", "ER015"),
    ("ER016", "ER016"),
    ("WR002", "WR002"),
    ("WR003", "WR003"),
    ("WR004", "WR004"),
    ("WR005", "WR005"),
    ("WR006", "WR006"),
    ("WR007", "WR007"),
    ("WR008", "WR008"),
    ("WR009", "WR009"),
    ("ES001", "ES001"),
    ("ES002", "ES002"),
    ("ES003", "ES003"),
]


@pytest.mark.parametrize("stem_prefix,expected_code", INVALID_CASES)
def test_invalid_file_emits_code(stem_prefix, expected_code):
    _reset_all_check_state()
    files = list(INVALID_DIR.glob(f"{stem_prefix}_*.L5X"))
    assert len(files) == 1, (
        f"Expected 1 file matching {stem_prefix}_*.L5X, found {len(files)}"
    )
    result = parse_l5x(files[0])
    assert isinstance(result, Success), (
        f"Parse failed for {files[0].name}: {result.failure()}"
    )
    project = result.unwrap()

    ar = analyze(project.controller).unwrap()
    codes = {d.code for d in ar.diagnostics}
    assert expected_code in codes, (
        f"Expected {expected_code} in diagnostics for {files[0].name}, "
        f"got {sorted(codes)}"
    )
