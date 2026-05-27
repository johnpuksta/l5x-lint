from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from returns.result import safe

from l5x_lint.domain.models import L5XProject
from l5x_lint.infrastructure.parsers._factory import create_parser


@safe
def parse_l5x(source: str | Path) -> L5XProject:
    """Parse L5X XML string or file path into domain models.

    Automatically selects the correct schema-version parser based on the
    ``SoftwareRevision`` attribute in the L5X file.
    """
    if isinstance(source, Path):
        root = ET.parse(source).getroot()
    elif isinstance(source, str):
        path = Path(source)
        if path.exists():
            root = ET.parse(str(path)).getroot()
        else:
            root = ET.fromstring(source)
    else:
        raise TypeError(f"Expected str or Path, got {type(source).__name__}")

    schema_revision = root.get("SchemaRevision", "")
    software_revision = root.get("SoftwareRevision", "")

    controller_el = root.find("Controller")
    if controller_el is None:
        raise ValueError("No <Controller> element found in L5X")

    parser = create_parser(software_revision, schema_revision)
    controller = parser.parse_controller(controller_el)

    return L5XProject(
        schema_revision=schema_revision,
        software_revision=software_revision,
        controller=controller,
    )
