from __future__ import annotations

import xml.etree.ElementTree as ET

from domain.models import (
    AOI,
    Controller,
    DataType,
    Member,
    Module,
    Program,
    Routine,
    Tag,
    Task,
)


def _parse_dimensions(dim_str: str | None) -> tuple[int, ...]:
    if not dim_str or dim_str.strip() == "":
        return ()
    raw = dim_str.strip().replace(",", " ")
    parts = [p for p in raw.split(" ") if p]
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return ()


def _parse_member_dimension(dim_str: str | None) -> int:
    if not dim_str:
        return 0
    try:
        return int(dim_str.strip())
    except ValueError:
        return 0


def _get_text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


def _get_description(el: ET.Element) -> str:
    desc = el.find("Description")
    if desc is None:
        return ""
    return _get_text(desc)


class L5XParser:
    """Base L5X parser — handles schema revisions v32 through v37.

    Core structural elements (data types, tags, routines, tasks, programs,
    modules) are stable across v32-v37. Version-specific subclasses override
    methods only when the XML structure changes between schema revisions.
    """

    software_revision: str
    schema_revision: str

    def __init__(self, software_revision: str, schema_revision: str) -> None:
        self.software_revision = software_revision
        self.schema_revision = schema_revision

    def parse_controller(self, controller_el: ET.Element) -> Controller:
        return Controller(
            name=controller_el.get("Name", ""),
            processor_type=controller_el.get("ProcessorType"),
            data_types=self.parse_data_types(controller_el.find("DataTypes")),
            tags=self.parse_tags(controller_el.find("Tags")),
            tasks=self.parse_tasks(controller_el.find("Tasks")),
            programs=self.parse_programs(controller_el.find("Programs")),
            aois=self.parse_aois(controller_el.find("AddOnInstructionDefinitions")),
            modules=self.parse_modules(controller_el.find("Modules")),
        )

    def parse_data_types(self, dt_el: ET.Element | None) -> list[DataType]:
        if dt_el is None:
            return []
        data_types: list[DataType] = []
        for dt in dt_el.findall("DataType"):
            name = dt.get("Name", "")
            family = dt.get("Family", "")
            class_ = dt.get("Class", "")
            members: list[Member] = []
            members_el = dt.find("Members")
            if members_el is not None:
                for m in members_el.findall("Member"):
                    m_name = m.get("Name", "")
                    m_dt = m.get("DataType", "")
                    m_dim = _parse_member_dimension(m.get("Dimension"))
                    m_bit = None
                    bit_str = m.get("BitNumber")
                    if bit_str is not None:
                        try:
                            m_bit = int(bit_str.strip())
                        except ValueError:
                            pass
                    members.append(
                        Member(
                            name=m_name,
                            data_type=m_dt,
                            dimension=m_dim,
                            bit_number=m_bit,
                        )
                    )
            data_types.append(
                DataType(
                    name=name,
                    family=family,
                    class_=class_,
                    members=members,
                )
            )
        return data_types

    def parse_tags(
        self,
        tags_el: ET.Element | None,
        tag_tag: str = "Tag",
        scope: str = "controller",
    ) -> list[Tag]:
        if tags_el is None:
            return []
        tags: list[Tag] = []
        for t in tags_el.findall(tag_tag):
            tags.append(self._parse_tag_element(t, tag_tag, scope))
        return tags

    def _parse_tag_element(
        self,
        el: ET.Element,
        tag_tag: str,
        scope: str,
    ) -> Tag:
        init_count = None
        data_el = el.find("Data")
        has_init = data_el is not None
        if data_el is not None and data_el.get("Format") == "Decorated":
            array_el = data_el.find("Array")
            if array_el is not None:
                elements = array_el.findall("Element")
                init_count = len(elements)
        return Tag(
            name=el.get("Name", ""),
            data_type=el.get("DataType", ""),
            dimensions=_parse_dimensions(el.get("Dimensions", "")),
            scope=scope,
            description=_get_description(el),
            initial_values=init_count,
            constant=el.get("Constant", "false") == "true",
            has_initial_value=has_init,
        )

    def parse_routines(self, routines_el: ET.Element | None) -> list[Routine]:
        if routines_el is None:
            return []
        routines: list[Routine] = []
        for r in routines_el.findall("Routine"):
            name = r.get("Name", "")
            type_ = r.get("Type", "")
            cdata = ""
            rll_el = r.find("RLLContent")
            if rll_el is not None:
                parts: list[str] = []
                for rung in rll_el.findall("Rung"):
                    text_el = rung.find("Text")
                    if text_el is not None and text_el.text:
                        parts.append(text_el.text.strip())
                cdata = "\n".join(parts)
            st_el = r.find("STContent")
            if st_el is not None:
                line_parts: list[str] = []
                for line in st_el.findall("Line"):
                    if line.text:
                        line_parts.append(line.text.strip())
                if line_parts:
                    cdata = "\n".join(line_parts)
                elif st_el.text and st_el.text.strip():
                    cdata = st_el.text.strip()
            routines.append(
                Routine(
                    name=name,
                    type=type_,
                    cdata=cdata,
                )
            )
        return routines

    def parse_tasks(self, tasks_el: ET.Element | None) -> list[Task]:
        if tasks_el is None:
            return []
        tasks: list[Task] = []
        for t in tasks_el.findall("Task"):
            name = t.get("Name", "")
            programs: list[str] = []
            sp_el = t.find("ScheduledPrograms")
            if sp_el is not None:
                for sp in sp_el.findall("ScheduledProgram"):
                    p_name = sp.get("Name")
                    if p_name:
                        programs.append(p_name)
            tasks.append(Task(name=name, programs=programs))
        return tasks

    def parse_aois(self, aoi_el: ET.Element | None) -> list[AOI]:
        if aoi_el is None:
            return []
        aois: list[AOI] = []
        for a in aoi_el.findall("AddOnInstructionDefinition"):
            aois.append(self._parse_aoi_element(a))
        return aois

    def _parse_aoi_element(self, a: ET.Element) -> AOI:
        name = a.get("Name", "")
        revision = a.get("Revision", "1.0")
        parameters: list = []
        params_el = a.find("Parameters")
        if params_el is not None:
            for p in params_el.findall("Parameter"):
                param = self._parse_aoi_parameter(p)
                parameters.append(param)
        local_tags: list[Tag] = self.parse_tags(
            a.find("LocalTags"),
            tag_tag="LocalTag",
            scope=f"aoi:{name}",
        )
        return AOI(
            name=name,
            revision=revision,
            parameters=parameters,
            local_tags=local_tags,
        )

    def _parse_aoi_parameter(self, p: ET.Element) -> dict:
        return {
            "name": p.get("Name", ""),
            "data_type": p.get("DataType", ""),
            "usage": p.get("Usage", ""),
            "required": p.get("Required", "false") == "true",
        }

    def parse_modules(self, modules_el: ET.Element | None) -> list[Module]:
        if modules_el is None:
            return []
        modules: list[Module] = []
        for m in modules_el.findall("Module"):
            modules.append(self._parse_module_element(m))
        return modules

    def _parse_module_element(self, m: ET.Element) -> Module:
        return Module(
            name=m.get("Name", ""),
            parent=m.get("ParentModule"),
        )

    def parse_programs(self, programs_el: ET.Element | None) -> list[Program]:
        if programs_el is None:
            return []
        programs: list[Program] = []
        for p in programs_el.findall("Program"):
            name = p.get("Name", "")
            tags_el = p.find("Tags")
            tags = self.parse_tags(tags_el, scope=f"program:{name}")
            routines_el = p.find("Routines")
            routines = self.parse_routines(routines_el)
            programs.append(
                Program(
                    name=name,
                    tags=tags,
                    routines=routines,
                )
            )
        return programs
