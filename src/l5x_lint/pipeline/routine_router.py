from returns.pipeline import flow
from returns.pointfree import bind
from returns.result import Failure, Result, Success

from l5x_lint.domain.errors import LintInternalError
from l5x_lint.domain.models import Controller
from l5x_lint.domain.rll_models import ParsedRung
from l5x_lint.domain.st_models import StProgram
from l5x_lint.pipeline import rung_parser, st_parser

_ROUTABLE = frozenset({"RLL", "ST"})


def route_routines(controller: Controller) -> Result[Controller, LintInternalError]:
    return flow(
        Success(controller),
        bind(_parse_all_routines),
    )


def _parse_all_routines(
    controller: Controller,
) -> Result[Controller, LintInternalError]:
    for prog in controller.programs:
        for r in prog.routines:
            if not r.cdata or r.type not in _ROUTABLE:
                continue
            parsed = _parse_by_type(r.type, r.cdata)
            result = parsed.map(lambda v: _assign(r, r.type, v))
            match result:
                case Failure():
                    return Failure(result.failure)
    return Success(controller)


def _assign(routine, type_, value):
    if type_ == "RLL":
        routine.rll_rungs = value
    elif type_ == "ST":
        routine.st_body = value


_Routable = list[ParsedRung] | StProgram


def _parse_by_type(type_: str, cdata: str) -> Result[_Routable, LintInternalError]:
    if type_ == "RLL":
        return rung_parser.parse(cdata)
    elif type_ == "ST":
        return st_parser.parse(cdata)
    return Success([])
