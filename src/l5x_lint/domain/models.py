from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TagPathSegment:
    name: str
    index: int | None = None

    def path_str(self) -> str:
        if self.index is not None:
            return f"{self.name}[{self.index}]"
        return self.name


@dataclass
class TagPath:
    segments: list[TagPathSegment]

    @property
    def full_name(self) -> str:
        return ".".join(s.path_str() for s in self.segments)

    def resolve(self, scope):
        raise NotImplementedError(
            "TagPath.resolve requires SymbolTable, not yet implemented"
        )


@dataclass
class Location:
    program: str
    routine: str
    rung: int | None = None
    line: int | None = None


@dataclass
class Member:
    name: str
    data_type: str
    dimension: int = 0
    bit_number: int | None = None


@dataclass
class DataType:
    name: str
    family: str
    class_: str
    members: list[Member] = field(default_factory=list)


@dataclass
class Tag:
    name: str
    data_type: str
    dimensions: tuple[int, ...] = ()
    scope: str = "controller"
    description: str = ""


@dataclass
class Routine:
    name: str
    type: str
    rll_rungs: list = field(default_factory=list)
    st_body: object = None
    cdata: str = ""


@dataclass
class Program:
    name: str
    tags: list[Tag] = field(default_factory=list)
    routines: list[Routine] = field(default_factory=list)


@dataclass
class Task:
    name: str
    programs: list[str] = field(default_factory=list)


@dataclass
class AOI:
    name: str
    revision: str = "1.0"
    parameters: list = field(default_factory=list)
    local_tags: list[Tag] = field(default_factory=list)


@dataclass
class Module:
    name: str
    parent: str | None = None


@dataclass
class Controller:
    name: str
    processor_type: str | None = None
    data_types: list[DataType] = field(default_factory=list)
    tags: list[Tag] = field(default_factory=list)
    programs: list[Program] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    aois: list[AOI] = field(default_factory=list)
    modules: list[Module] = field(default_factory=list)


@dataclass
class L5XProject:
    schema_revision: str
    software_revision: str
    controller: Controller
