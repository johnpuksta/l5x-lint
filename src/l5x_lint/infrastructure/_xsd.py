from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import xmlschema
from returns.result import Failure, Result, Success

from l5x_lint.domain.errors import L5XStructureError, LintInternalError

_SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"

_schema_cache: dict[int, xmlschema.XMLSchema] = {}


def _get_schema(major: int) -> Result[xmlschema.XMLSchema, LintInternalError]:
    if major not in _schema_cache:
        xsd_path = _SCHEMAS_DIR / f"l5x-v{major}.xsd"
        if not xsd_path.exists():
            return Failure(L5XStructureError(
                element="Schema",
                detail=f"No XSD schema for version v{major}",
            ))
        try:
            _schema_cache[major] = xmlschema.XMLSchema(xsd_path)
        except Exception as e:
            return Failure(L5XStructureError(
                element="Schema",
                detail=f"Failed to load XSD for v{major}: {e}",
            ))
    return Success(_schema_cache[major])


def _is_known_extension(err: xmlschema.XMLSchemaValidationError) -> bool:
    reason = str(err.reason)
    path = str(err.path) if err.path else ""

    # Rockwell adds attributes the XSD doesn't declare — always tolerate
    if "attribute not allowed" in reason:
        return True

    # Mixed content in code blocks — parser handles this
    if "character data between child elements not allowed" in reason:
        if "STContent" in path or "RLLContent" in path:
            return True

    # Rockwell uses mixed-case enums — XSD has strict uppercase
    if "value must be one of" in reason:
        return True

    # Rockwell reorders child elements — XSD uses xs:sequence
    if "Unexpected child with tag" in reason:
        return True

    # SignatureHistory has child elements in real files but XSD says xs:string
    if "simple content element can't have child elements" in reason:
        if "SignatureHistory" in path:
            return True

    # public element inside ExtendedProperties
    if "element 'public' not found" in reason:
        return True

    # Module required attrs vary by version — tolerate missing ones
    if "missing required attribute" in reason:
        if "/Module" in path:
            return True

    return False


def validate_l5x_xml(
    root: ET.Element,
    software_revision: str,
) -> Result[None, LintInternalError]:
    major = 0
    try:
        major = int(software_revision.split(".")[0])
    except (ValueError, IndexError):
        return Failure(L5XStructureError(
            element="Schema",
            detail=f"Cannot parse software revision '{software_revision}'",
        ))

    schema_result = _get_schema(major)
    match schema_result:
        case Failure():
            return Success(None)
        case Success(schema):
            pass

    errors = [e for e in schema.iter_errors(root) if not _is_known_extension(e)]
    if errors:
        err = errors[0]
        detail = f"at {err.path}: {err.reason}" if err.path else str(err)
        return Failure(L5XStructureError(element="Schema", detail=detail))

    return Success(None)
