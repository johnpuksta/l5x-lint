from dataclasses import dataclass, field

from l5x_lint.domain.models import TagPath


@dataclass
class StBinaryOp:
    left: "StExpression"
    op: str
    right: "StExpression"


@dataclass
class StUnaryOp:
    op: str
    operand: "StExpression"


@dataclass
class StLiteral:
    value: int | float | str | bool


@dataclass
class StTagRef:
    path: TagPath


@dataclass
class StCall:
    name: str
    args: list["StExpression"] = field(default_factory=list)
    line: int = 0


StExpression = StBinaryOp | StUnaryOp | StLiteral | StTagRef | StCall


@dataclass
class StAssignment:
    target: TagPath
    expression: StExpression
    line: int = 0


@dataclass
class StIf:
    condition: StExpression
    body: list["StStatement"] = field(default_factory=list)
    elsif_pairs: list[tuple[StExpression, list["StStatement"]]] = field(
        default_factory=list
    )
    else_body: list["StStatement"] = field(default_factory=list)
    line: int = 0


@dataclass
class StCase:
    expression: StExpression
    cases: list[tuple[list[StExpression], list["StStatement"]]] = field(
        default_factory=list
    )
    else_body: list["StStatement"] = field(default_factory=list)
    line: int = 0


@dataclass
class StFor:
    variable: TagPath
    start: StExpression
    end: StExpression
    step: StExpression | None = None
    body: list["StStatement"] = field(default_factory=list)
    line: int = 0


@dataclass
class StWhile:
    condition: StExpression
    body: list["StStatement"] = field(default_factory=list)
    line: int = 0


@dataclass
class StRepeat:
    body: list["StStatement"] = field(default_factory=list)
    until: StExpression | None = None
    line: int = 0


@dataclass
class StJsr:
    routine_name: str
    args: list[StExpression] = field(default_factory=list)
    line: int = 0


@dataclass
class StExit:
    line: int = 0


@dataclass
class StReturn:
    line: int = 0


StStatement = (
    StAssignment
    | StIf
    | StCase
    | StFor
    | StWhile
    | StRepeat
    | StCall
    | StJsr
    | StExit
    | StReturn
)


@dataclass
class StProgram:
    statements: list[StStatement] = field(default_factory=list)
