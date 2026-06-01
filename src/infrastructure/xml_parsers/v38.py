from __future__ import annotations

import xml.etree.ElementTree as ET

from infrastructure.xml_parsers.base import L5XParser


class L5XParserV38(L5XParser):
    """L5X parser for schema revision v38+.

    Structural differences from v32-v37:
      - ``AliasFor`` attribute removed from ``AOIParameterType``.
        ``_parse_aoi_parameter`` no longer reads it.
      - ``OldName`` and ``DataExchangeId`` attributes added to
        ``ControllerType``, ``TagType``, and ``ModuleType``.
        Not captured by domain models.
      - ``Use`` attribute added to ``TagType`` and ``ModuleType``.
        Not captured by domain models.
      - ``DataLogs`` child element removed from ``ControllerType``.
      - ``RcpGatewayAddress1`` / ``RcpGatewayAddress2`` added to ``PortType``.
        Not captured by domain models.
      - Module ``Vendor``, ``ProductType``, ``ProductCode``, ``Major``,
        ``Minor`` changed from required to optional.
        Not captured by domain models.
    """

    def _parse_aoi_parameter(self, p: ET.Element) -> dict:
        name = p.get("Name", "")
        data_type = p.get("DataType", "")
        usage = p.get("Usage", "")
        required = False
        req = p.get("Required")
        if req is not None and req.lower() in ("true", "1"):
            required = True
        return {
            "name": name,
            "data_type": data_type,
            "usage": usage,
            "required": required,
        }
