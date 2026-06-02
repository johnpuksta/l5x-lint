from dataclasses import dataclass, field

from returns.maybe import Maybe, Nothing, Some

from domain.models import AOI, Controller, DataType, Tag

BUILTIN_TYPES: set[str] = {
    "BOOL",
    "SINT",
    "INT",
    "DINT",
    "LINT",
    "USINT",
    "UINT",
    "UDINT",
    "ULINT",
    "REAL",
    "LREAL",
    "STRING",
    "BYTE",
    "WORD",
    "DWORD",
    "LWORD",
    "TIMER",
    "COUNTER",
    "CONTROL",
    "MESSAGE",
}


@dataclass
class SymbolTable:
    controller_tags: dict[str, Tag] = field(default_factory=dict)
    program_tags: dict[str, dict[str, Tag]] = field(default_factory=dict)
    aoi_tags: dict[str, dict[str, Tag]] = field(default_factory=dict)
    data_types: dict[str, DataType] = field(default_factory=dict)
    routine_names: set[str] = field(default_factory=set)
    aoi_names: set[str] = field(default_factory=set)
    aoi_list: list[AOI] = field(default_factory=list)
    duplicate_controller_tags: list[str] = field(default_factory=list)
    duplicate_program_tags: dict[str, list[str]] = field(default_factory=dict)

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

    def resolve_type(self, name: str, program: str | None = None) -> DataType | None:
        match self.resolve(name, program):
            case Some(tag):
                dt = self.data_types.get(tag.data_type)
                if dt is not None:
                    return dt
                if tag.data_type.upper() in BUILTIN_TYPES:
                    return DataType(
                        name=tag.data_type.upper(), family="BuiltIn", class_=""
                    )
                return None
            case _:
                return None

    def resolve_member_type(self, base_type: str, member: str) -> DataType | None:
        dt = self.data_types.get(base_type)
        if dt is None:
            return None
        for m in dt.members:
            if m.name == member:
                return self.data_types.get(m.data_type)
        return None

    def tag_in_other_program(self, name: str, current_program: str) -> bool:
        for prog_name, tags in self.program_tags.items():
            if prog_name != current_program and name in tags:
                return True
        return False


def build_symbol_table(controller: Controller) -> SymbolTable:
    controller_tags: dict[str, Tag] = {}
    program_tags: dict[str, dict[str, Tag]] = {}
    aoi_tags: dict[str, dict[str, Tag]] = {}
    duplicate_controller_tags: list[str] = []
    duplicate_program_tags: dict[str, list[str]] = {}

    for t in controller.tags:
        if t.name in controller_tags:
            duplicate_controller_tags.append(t.name)
        controller_tags[t.name] = t

    for prog in controller.programs:
        prog_tags: dict[str, Tag] = {}
        prog_dupes: list[str] = []
        for t in prog.tags:
            if t.name in prog_tags:
                prog_dupes.append(t.name)
            prog_tags[t.name] = t
        program_tags[prog.name] = prog_tags
        if prog_dupes:
            duplicate_program_tags[prog.name] = prog_dupes

    for aoi in controller.aois:
        aoi_local: dict[str, Tag] = {}
        for t in aoi.local_tags:
            aoi_local[t.name] = t
        aoi_tags[aoi.name] = aoi_local

    data_types: dict[str, DataType] = {}
    for dt in controller.data_types:
        data_types[dt.name] = dt

    routine_names: set[str] = set()
    for prog in controller.programs:
        for r in prog.routines:
            routine_names.add(r.name)

    aoi_names = {aoi.name for aoi in controller.aois}

    return SymbolTable(
        controller_tags=controller_tags,
        program_tags=program_tags,
        aoi_tags=aoi_tags,
        data_types=data_types,
        routine_names=routine_names,
        aoi_names=aoi_names,
        aoi_list=list(controller.aois),
        duplicate_controller_tags=duplicate_controller_tags,
        duplicate_program_tags=duplicate_program_tags,
    )
