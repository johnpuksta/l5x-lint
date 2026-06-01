from conftest import CUSTOM_DIR, INVALID_DIR, VALID_DIR


def test_valid_files_exist():
    files = list(VALID_DIR.rglob("*.L5X"))
    assert len(files) >= 24, f"Expected at least 24 valid L5X files, found {len(files)}"
    for f in files:
        assert f.stat().st_size > 0, f"{f.name} is empty"


def test_invalid_files_exist():
    files = list(INVALID_DIR.glob("*.L5X"))
    expected = {
        "EC001",
        "EC002",
        "EC003",
        "EC004",
        "EC005",
        "EC006",
        "EC007",
        "ER009",
        "EC010",
        "WC001",
        "WR002",
        "WR003",
        "WR004",
        "WC005",
        "EC011",
        "EC012",
        "EC013",
        "EC014",
        "EC015",
        "EC016",
        "EC017",
        "EC018",
        "WC103",
        "WC106",
        "WC107",
        "WC108",
        "WS101",
        "WS102",
        "WS104",
        "WS105",
        "WS107",
        "WS108",
        "WS109",
        "WS110",
        "WS111",
        "WS112",
        "WS113",
        "WS114",
        "WS115",
        "WS116",
        "WS117",
        "WS118",
        "ER013",
        "ER014",
        "ER015",
        "ER016",
        "WR005",
        "WR006",
        "WR007",
        "WR008",
        "WR009",
        "ES001",
        "ES002",
        "ES003",
    }
    found = {f.stem.split("_")[0] for f in files}
    missing = expected - found
    extra = found - expected
    assert not missing, f"Missing test files for codes: {missing}"
    assert not extra, f"Unexpected test files for codes: {extra}"


def test_custom_files_exist():
    files = list(CUSTOM_DIR.glob("*.L5X"))
    assert len(files) >= 5, f"Expected at least 5 custom L5X files, found {len(files)}"
    for f in files:
        assert f.stat().st_size > 0, f"{f.name} is empty"


def test_custom_files_are_valid_xml():
    import xml.etree.ElementTree as ET

    for f in CUSTOM_DIR.glob("*.L5X"):
        root = ET.parse(f).getroot()
        assert root.tag == "RSLogix5000Content", f"{f.name}: unexpected root tag"
        assert root.find("Controller") is not None, f"{f.name}: missing Controller"


def test_invalid_files_are_valid_xml():
    import xml.etree.ElementTree as ET

    for f in INVALID_DIR.glob("*.L5X"):
        tree = ET.parse(f)
        root = tree.getroot()
        assert root.tag == "RSLogix5000Content", f"{f.name}: unexpected root tag"
        assert root.find("Controller") is not None, f"{f.name}: missing Controller"
