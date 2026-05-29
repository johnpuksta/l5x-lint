from __future__ import annotations

from returns.result import Failure, Result, Success

from l5x_lint.domain.errors import LintInternalError, SoftwareRevisionError
from l5x_lint.infrastructure.parsers.base import L5XParser
from l5x_lint.infrastructure.parsers.v38 import L5XParserV38

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

    cls = _PARSER_REGISTRY.get(major, L5XParser)
    return Success(cls(software_revision, schema_revision))
