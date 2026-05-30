import dataclasses as _dc
from dataclasses import dataclass
from typing import ClassVar


class LintErrorBase:
    code: ClassVar[str]
    severity: ClassVar[str]
    description: ClassVar[str]
    message_template: ClassVar[str]

    @property
    def message(self) -> str:
        fields = {f.name: getattr(self, f.name) for f in _dc.fields(self)}
        return self.message_template.format(**fields)


@dataclass
class EC001(LintErrorBase):
    code: ClassVar[str] = "EC001"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Undefined tag reference '{name}'"
    description: ClassVar[str] = (
        "A tag reference in a rung or ST statement does not match any "
        "declared tag in the controller or program scope."
    )
    name: str


@dataclass
class EC002(LintErrorBase):
    code: ClassVar[str] = "EC002"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "Type mismatch: expected '{expected}', got '{actual}'"
    )
    description: ClassVar[str] = (
        "An instruction operand has an incompatible data type. "
        "For example, a TON instruction requires a TIMER tag, not a DINT."
    )
    expected: str
    actual: str


@dataclass
class EC003(LintErrorBase):
    code: ClassVar[str] = "EC003"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Missing AOI definition '{name}'"
    description: ClassVar[str] = (
        "An Add-On Instruction is referenced but no matching "
        "AddOnInstructionDefinition exists in the project."
    )
    name: str


@dataclass
class EC004(LintErrorBase):
    code: ClassVar[str] = "EC004"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "Invalid JSR target: routine '{routine}' not found"
    )
    description: ClassVar[str] = (
        "A JSR (Jump to Subroutine) instruction targets a routine "
        "name that does not exist in any program."
    )
    routine: str


@dataclass
class EC005(LintErrorBase):
    code: ClassVar[str] = "EC005"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "Invalid UDT member access: '{path}.{member}' does not exist"
    )
    description: ClassVar[str] = (
        "A tag member access references a member that does not exist "
        "on the tag's data type."
    )
    path: str
    member: str


@dataclass
class EC006(LintErrorBase):
    code: ClassVar[str] = "EC006"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "Array index out of bounds: '{name}[{index}]' exceeds size {size}"
    )
    description: ClassVar[str] = (
        "An array index is outside the declared dimension. "
        "Arrays are 0-indexed, so index {size-1} is the last valid position."
    )
    name: str
    index: int
    size: int


@dataclass
class EC007(LintErrorBase):
    code: ClassVar[str] = "EC007"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Duplicate tag name '{name}' in scope '{scope}'"
    description: ClassVar[str] = (
        "Two or more tags share the same name within the same scope "
        "(controller or program)."
    )
    name: str
    scope: str


@dataclass
class EC008(LintErrorBase):
    code: ClassVar[str] = "EC008"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "AOI circular dependency: {chain}"
    description: ClassVar[str] = (
        "Add-On Instructions form a circular call chain, "
        "which would cause infinite recursion at runtime."
    )
    chain: list[str]

    @property
    def message(self) -> str:
        return f"AOI circular dependency: {' -> '.join(self.chain)}"


@dataclass
class ER009(LintErrorBase):
    code: ClassVar[str] = "ER009"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "Wrong operand count for {opcode}: expected {expected}, got {actual}"
    )
    description: ClassVar[str] = (
        "An instruction has too few or too many operands compared "
        "to its required operand count."
    )
    opcode: str
    expected: int
    actual: int


@dataclass
class EC010(LintErrorBase):
    code: ClassVar[str] = "EC010"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "Cross-scope tag violation: '{name}' accessed from "
        "'{accessed_from}', declared in '{declared_in}'"
    )
    description: ClassVar[str] = (
        "A program-scoped tag is referenced from a different program. "
        "Program tags are private to their declaring program."
    )
    name: str
    accessed_from: str
    declared_in: str


@dataclass
class WC001(LintErrorBase):
    code: ClassVar[str] = "WC001"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Unused tag '{name}' declared but never referenced"
    )
    description: ClassVar[str] = (
        "A tag is declared but never read or written in any routine. "
        "This may indicate dead code or a missing reference."
    )
    name: str


@dataclass
class WR002(LintErrorBase):
    code: ClassVar[str] = "WR002"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Unreachable rung {rung}: first instruction is AFI"
    )
    description: ClassVar[str] = (
        "A rung begins with AFI (Always False Input), causing the "
        "entire rung to never execute. All rungs after this one "
        "should be reviewed."
    )
    rung: int


@dataclass
class WR003(LintErrorBase):
    code: ClassVar[str] = "WR003"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Output '{name}' is never driven (used in input only)"
    )
    description: ClassVar[str] = (
        "A tag is used as an input condition (XIC, XIO) but never "
        "written by an output instruction (OTE, OTL, OTU). "
        "Its value is never set by this program."
    )
    name: str


@dataclass
class WR004(LintErrorBase):
    code: ClassVar[str] = "WR004"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "Timer '{name}' PRE is never set (still 0)"
    description: ClassVar[str] = (
        "A timer's PRE (Preset) value is 0, which means the timer "
        "will never time out. This is likely a logic error."
    )
    name: str


@dataclass
class WC005(LintErrorBase):
    code: ClassVar[str] = "WC005"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "Tag '{name}' is shadowed by '{hidden_by}'"
    description: ClassVar[str] = (
        "A program-scoped tag has the same name as a controller-scoped "
        "tag. The program tag takes precedence and the controller tag "
        "is inaccessible within that program."
    )
    name: str
    hidden_by: str




@dataclass
class EC011(LintErrorBase):
    code: ClassVar[str] = "EC011"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Reserved name collision: '{name}' shadows built-in"
    description: ClassVar[str] = (
        "A user-defined POU (AOI, program, function block) has the same "
        "name as a built-in instruction or type, causing name shadowing."
    )
    name: str
    kind: str = "POU"


@dataclass
class EC012(LintErrorBase):
    code: ClassVar[str] = "EC012"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "Array initializer element count mismatch: got {actual}, "
        "expected {expected}"
    )
    description: ClassVar[str] = (
        "The number of initializer elements in a tag's <Data> does not "
        "match the declared array dimension product."
    )
    name: str
    expected: int
    actual: int


@dataclass
class WS101(LintErrorBase):
    code: ClassVar[str] = "WS101"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Floating-point equality comparison: '{text}' may be unreliable"
    )
    description: ClassVar[str] = (
        "Direct equality (==) or inequality (<>) of REAL/LREAL values "
        "is unreliable due to floating-point precision. Use a tolerance "
        "check (ABS(a - b) < 0.0001) instead."
    )
    text: str


@dataclass
class WS102(LintErrorBase):
    code: ClassVar[str] = "WS102"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "Division by literal zero: {text}"
    description: ClassVar[str] = (
        "A division or MOD operation uses a literal zero as divisor. "
        "This causes a runtime division-by-zero error."
    )
    text: str


@dataclass
class WC103(LintErrorBase):
    code: ClassVar[str] = "WC103"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Cyclomatic complexity {complexity} exceeds threshold {threshold}"
    )
    description: ClassVar[str] = (
        "The routine has too many branching points (IF, CASE, loops, "
        "XIC/XIO branches). Consider refactoring into smaller routines."
    )
    complexity: int
    threshold: int = 15


@dataclass
class WS104(LintErrorBase):
    code: ClassVar[str] = "WS104"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "Non-BOOL condition in {construct}: got '{actual}'"
    description: ClassVar[str] = (
        "A control-flow construct (IF, WHILE, UNTIL) uses a condition "
        "that is not BOOL. Only BOOL expressions are valid conditions."
    )
    construct: str
    actual: str


@dataclass
class WS105(LintErrorBase):
    code: ClassVar[str] = "WS105"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Implicit downcast in assignment to '{name}': "
        "'{from_type}' -> '{to_type}' loses precision"
    )
    description: ClassVar[str] = (
        "A value is assigned to a narrower type, causing potential "
        "precision loss or overflow."
    )
    name: str
    from_type: str
    to_type: str


@dataclass
class WC106(LintErrorBase):
    code: ClassVar[str] = "WC106"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Unused POU '{name}' is defined but never referenced"
    )
    description: ClassVar[str] = (
        "A program, AOI, or routine is defined in the project but "
        "never called or referenced from any other POU."
    )
    name: str
    kind: str = "POU"


@dataclass
class WS107(LintErrorBase):
    code: ClassVar[str] = "WS107"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Missing ELSE in {construct} — not all branches are covered"
    )
    description: ClassVar[str] = (
        "An IF or CASE statement lacks an ELSE branch, meaning some "
        "conditions may silently fall through without assignment."
    )
    construct: str



@dataclass
class ER013(LintErrorBase):
    code: ClassVar[str] = "ER013"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Invalid JMP target: label '{label}' not found"
    description: ClassVar[str] = (
        "A JMP instruction references a label that has no "
        "matching LBL instruction in the routine."
    )
    label: str


@dataclass
class ER014(LintErrorBase):
    code: ClassVar[str] = "ER014"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "OTL without OTU: '{name}' is latched but never unlatched"
    )
    description: ClassVar[str] = (
        "An OTL instruction sets a tag but no corresponding OTU "
        "unsets it, which may cause unintended behavior."
    )
    name: str


@dataclass
class EC013(LintErrorBase):
    code: ClassVar[str] = "EC013"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Duplicate JMP label '{label}'"
    description: ClassVar[str] = (
        "Two or more LBL instructions use the same label name "
        "within the same program."
    )
    label: str


@dataclass
class EC015(LintErrorBase):
    code: ClassVar[str] = "EC015"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "Invalid/undeclared data type '{data_type}' used by '{tag_name}'"
    )
    description: ClassVar[str] = (
        "A tag is declared with a data type that does not exist "
        "in the project or as a built-in type."
    )
    tag_name: str
    data_type: str


@dataclass
class EC017(LintErrorBase):
    code: ClassVar[str] = "EC017"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Cannot modify constant tag '{name}'"
    description: ClassVar[str] = (
        "An assignment targets a CONSTANT tag. Constant tags "
        "cannot be modified at runtime."
    )
    name: str


@dataclass
class WR005(LintErrorBase):
    code: ClassVar[str] = "WR005"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = "NOP instruction present at rung {rung}"
    description: ClassVar[str] = (
        "A NOP (No Operation) instruction is present. NOPs are "
        "no-ops that indicate dead or debugging code."
    )
    rung: int


@dataclass
class WR006(LintErrorBase):
    code: ClassVar[str] = "WR006"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "SUS instruction present at rung {rung} — "
        "should not be in production"
    )
    description: ClassVar[str] = (
        "A SUS (Suspend) instruction is present. SUS is a debug "
        "breakpoint that should be removed before production deployment."
    )
    rung: int


@dataclass
class WR007(LintErrorBase):
    code: ClassVar[str] = "WR007"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Rung {rung} has input conditions but no output instruction"
    )
    description: ClassVar[str] = (
        "A rung contains input conditions (XIC, XIO) but no output "
        "instruction (OTE, OTL, OTU), so it has no effect."
    )
    rung: int


@dataclass
class WS108(LintErrorBase):
    code: ClassVar[str] = "WS108"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Statement with no effect at line {line}"
    )
    description: ClassVar[str] = (
        "An expression statement has no side effects and its "
        "result is discarded."
    )
    line: int


@dataclass
class WS109(LintErrorBase):
    code: ClassVar[str] = "WS109"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Assignment to FOR loop variable '{name}' at line {line}"
    )
    description: ClassVar[str] = (
        "Modifying the loop counter variable inside a FOR loop "
        "body can cause unexpected behavior."
    )
    name: str
    line: int


@dataclass
class WS110(LintErrorBase):
    code: ClassVar[str] = "WS110"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Dead code after {construct} at line {line}"
    )
    description: ClassVar[str] = (
        "Statements after RETURN or EXIT are unreachable and "
        "will never execute."
    )
    construct: str
    line: int


@dataclass
class WS113(LintErrorBase):
    code: ClassVar[str] = "WS113"
    severity: ClassVar[str] = "warning"
    message_template: ClassVar[str] = (
        "Non-BOOL operand for {op}: operand is '{actual}'"
    )
    description: ClassVar[str] = (
        "The AND_THEN and OR_ELSE short-circuit operators require "
        "BOOL operands."
    )
    op: str
    actual: str


@dataclass
class ES001(LintErrorBase):
    code: ClassVar[str] = "ES001"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = (
        "Invalid expression operation: {left_type} {op} {right_type}"
    )
    description: ClassVar[str] = (
        "An operation is not valid for the operand types "
        "(e.g., string addition with DINT)."
    )
    left_type: str
    op: str
    right_type: str


@dataclass
class ES002(LintErrorBase):
    code: ClassVar[str] = "ES002"
    severity: ClassVar[str] = "error"
    message_template: ClassVar[str] = "Duplicate CASE value '{value}' at line {line}"
    description: ClassVar[str] = (
        "A CASE statement has two branches with the same selector value. "
        "The second branch is unreachable."
    )
    value: str
    line: int


LintError = (
    EC001 | EC002 | EC003 | EC004 | EC005
    | EC006 | EC007 | EC008 | ER009 | EC010
    | EC011 | EC012 | EC013 | EC015 | EC017
    | ER013 | ER014
    | WC001 | WR002 | WR003 | WR004 | WC005
    | WC103 | WC106
    | WR005 | WR006 | WR007
    | WS101 | WS102 | WS104 | WS105 | WS107
    | WS108 | WS109 | WS110 | WS113
    | ES001 | ES002
)
