from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Operand:
    value: str
    type_hint: str | None = None


@dataclass
class Instruction:
    opcode: str
    operands: list[Operand] = field(default_factory=list)
    branch: list[list[Instruction]] | None = None
    is_output_branch: bool = False


@dataclass
class ParsedRung:
    number: int
    text: str
    instructions: list[Instruction] = field(default_factory=list)
    output_branches: list[list[Instruction]] = field(default_factory=list)
