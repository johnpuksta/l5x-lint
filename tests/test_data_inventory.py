from pathlib import Path
from conftest import VALID_DIR, INVALID_DIR


def test_valid_files_exist():
    files = list(VALID_DIR.rglob("*.L5X"))
    assert len(files) >= 14, f"Expected at least 14 valid L5X files, found {len(files)}"
    for f in files:
        assert f.stat().st_size > 0, f"{f.name} is empty"


def test_invalid_files_exist():
    files = list(INVALID_DIR.glob("*.L5X"))
    expected = {"E001", "E002", "E003", "E004", "E005", "E006", "E007", "E009", "E010",
                "W001", "W002", "W003", "W004", "W005"}
    found = {f.stem.split("_")[0] for f in files}
    missing = expected - found
    assert not missing, f"Missing test files for codes: {missing}"


def test_invalid_files_are_valid_xml():
    import xml.etree.ElementTree as ET
    for f in INVALID_DIR.glob("*.L5X"):
        tree = ET.parse(f)
        root = tree.getroot()
        assert root.tag == "RSLogix5000Content", f"{f.name}: unexpected root tag"
        assert root.find("Controller") is not None, f"{f.name}: missing Controller"
