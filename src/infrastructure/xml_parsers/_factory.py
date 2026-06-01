from __future__ import annotations

import warnings

from returns.result import Failure, Result, Success

from domain.errors import LintInternalError, SoftwareRevisionError
from infrastructure.xml_parsers.base import L5XParser
from infrastructure.xml_parsers.v38 import L5XParserV38

_MAX_KNOWN_VERSION = 38

_PARSER_REGISTRY: dict[int, type[L5XParser]] = {
    38: L5XParserV38,
}


def create_parser(
    software_revision: str, schema_revision: str
) -> Result[L5XParser, LintInternalError]:
    major = 0
    try:
        major = int(software_revision.split(".")[0])
    except (ValueError, IndexError):
        return Failure(SoftwareRevisionError(revision=software_revision))

    if major > _MAX_KNOWN_VERSION:
        warnings.warn(
            f"Software revision v{major} exceeds max known v{_MAX_KNOWN_VERSION} "
            f"— base parser will be used",
            UserWarning,
            stacklevel=2,
        )

    cls = _PARSER_REGISTRY.get(major, L5XParser)
    return Success(cls(software_revision, schema_revision))
