from returns.result import Failure, Result, Success

from l5x_lint.domain.models import Controller
from l5x_lint.pipeline import rung_parser, st_parser

_UNSUPPORTED = frozenset({"FBD", "SFC", "FUNCTION", "FUNCTION_BLOCK"})


def route_routines(controller: Controller) -> Result[Controller, Exception]:
    for prog in controller.programs:
        for r in prog.routines:
            if not r.cdata:
                continue
            if r.type in _UNSUPPORTED:
                continue
            result = _parse_by_type(r.type, r.cdata)
            match result:
                case Success(value):
                    if r.type == "RLL":
                        r.rll_rungs = value
                    elif r.type == "ST":
                        r.st_body = value
                case Failure():
                    return Failure(result.failure)
    return Success(controller)


def _parse_by_type(type_: str, cdata: str) -> Result:
    if type_ == "RLL":
        return rung_parser.parse(cdata)
    elif type_ == "ST":
        return st_parser.parse(cdata)
    return Success([])
