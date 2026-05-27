from __future__ import annotations

from l5x_lint.infrastructure.parsers.base import L5XParser
from l5x_lint.infrastructure.parsers.v38 import L5XParserV38

_PARSER_REGISTRY: dict[int, type[L5XParser]] = {
    38: L5XParserV38,
}


def create_parser(software_revision: str, schema_revision: str) -> L5XParser:
    """Return the appropriate parser for the given software revision.

    Dispatches on the major version of ``SoftwareRevision`` (e.g. ``"36.00"``
    → major 36 → base parser). Falls back to the base parser for unknown or
    unparseable revision strings.
    """
    major = 0
    try:
        major = int(software_revision.split(".")[0])
    except (ValueError, IndexError):
        pass

    cls = _PARSER_REGISTRY.get(major, L5XParser)
    return cls(software_revision, schema_revision)
