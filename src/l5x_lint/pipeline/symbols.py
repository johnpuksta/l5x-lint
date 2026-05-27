from dataclasses import dataclass, field

from returns.maybe import Maybe, Nothing, Some

from l5x_lint.domain.models import Controller, DataType, Tag


@dataclass
class SymbolTable:
    controller_tags: dict[str, Tag] = field(default_factory=dict)
    program_tags: dict[str, dict[str, Tag]] = field(default_factory=dict)
    aoi_tags: dict[str, dict[str, Tag]] = field(default_factory=dict)
    data_types: dict[str, DataType] = field(default_factory=dict)

    def resolve(self, name: str, program: str | None = None) -> Maybe[Tag]:
        if program and program in self.program_tags:
            if name in self.program_tags[program]:
                return Some(self.program_tags[program][name])
        if name in self.controller_tags:
            return Some(self.controller_tags[name])
        for aoi_name, tags in self.aoi_tags.items():
            if name in tags:
                return Some(tags[name])
        return Nothing


def build_symbol_table(controller: Controller) -> SymbolTable:
    controller_tags: dict[str, Tag] = {}
    program_tags: dict[str, dict[str, Tag]] = {}
    aoi_tags: dict[str, dict[str, Tag]] = {}

    for t in controller.tags:
        controller_tags[t.name] = t

    for prog in controller.programs:
        prog_tags: dict[str, Tag] = {}
        for t in prog.tags:
            prog_tags[t.name] = t
        program_tags[prog.name] = prog_tags

    for aoi in controller.aois:
        aoi_local: dict[str, Tag] = {}
        for t in aoi.local_tags:
            aoi_local[t.name] = t
        aoi_tags[aoi.name] = aoi_local

    data_types: dict[str, DataType] = {}
    for dt in controller.data_types:
        data_types[dt.name] = dt

    return SymbolTable(
        controller_tags=controller_tags,
        program_tags=program_tags,
        aoi_tags=aoi_tags,
        data_types=data_types,
    )
