from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from returns.result import Failure, Result, Success

from l5x_lint.domain.errors import (
    AdapterArgumentError,
    L5XStructureError,
    LintInternalError,
)
from l5x_lint.domain.models import L5XProject
from l5x_lint.infrastructure.parsers._factory import create_parser


def parse_l5x(source: str | Path) -> Result[L5XProject, LintInternalError]:
    try:
        if isinstance(source, Path):
            root = ET.parse(source).getroot()
        elif isinstance(source, str):
            path = Path(source)
            if path.exists():
                root = ET.parse(str(path)).getroot()
            else:
                root = ET.fromstring(source)
        else:
            return Failure(AdapterArgumentError(got=type(source).__name__))
    except (ET.ParseError, OSError) as e:
        return Failure(L5XStructureError(element="XML", detail=str(e)))

    schema_revision = root.get("SchemaRevision", "")
    software_revision = root.get("SoftwareRevision", "")

    controller_el = root.find("Controller")
    if controller_el is None:
        return Failure(L5XStructureError(
            element="Controller", detail="Not found in L5X root",
        ))

    parser_result = create_parser(software_revision, schema_revision)
    match parser_result:
        case Failure(err):
            return Failure(err)
        case Success(parser):
            controller = parser.parse_controller(controller_el)

    return Success(L5XProject(
        schema_revision=schema_revision,
        software_revision=software_revision,
        controller=controller,
    ))
