from dataclasses import dataclass


@dataclass
class L5XStructureError:
    element: str
    detail: str
    line: int | None = None

    def __str__(self) -> str:
        return self.detail


@dataclass
class RLLParseError:
    text: str
    position: int | None = None


@dataclass
class STParseError:
    text: str
    position: int | None = None


@dataclass
class UnsupportedRoutineError:
    routine_name: str
    routine_type: str


@dataclass
class SymbolTableError:
    detail: str


@dataclass
class AdapterArgumentError:
    got: str


@dataclass
class SoftwareRevisionError:
    revision: str


LintInternalError = (
    L5XStructureError
    | RLLParseError
    | STParseError
    | UnsupportedRoutineError
    | SymbolTableError
    | AdapterArgumentError
    | SoftwareRevisionError
)
