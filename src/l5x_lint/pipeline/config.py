from __future__ import annotations

from dataclasses import dataclass, field


_WARNING_NAMES = frozenset({
    "unused", "unreachable", "output", "timer", "shadowed",
    "numeric", "complexity", "conversion", "missing-else",
})

_ENABLEABLE = frozenset({"numeric", "complexity"})


@dataclass
class LintConfig:
    warn_unused: bool = True
    warn_unreachable: bool = True
    warn_output_never_driven: bool = True
    warn_timer_pre: bool = True
    warn_shadowed: bool = True
    warn_numeric_hazards: bool = False
    warn_complexity: bool = False
    warn_implicit_conversion: bool = True
    warn_missing_else: bool = True
    severity_overrides: dict[str, str] = field(default_factory=dict)
    rule_pack: str = "none"
    dialect: str = "rockwell"

    def apply_rule_pack(self) -> None:
        match self.rule_pack:
            case "safety":
                self.warn_numeric_hazards = True
                self.warn_unreachable = True
                self.severity_overrides.update({
                    "WC103": "error",
                    "WR002": "error",
                    "WS101": "error",
                    "WS102": "error",
                })
            case "rockwell":
                self.warn_numeric_hazards = False
            case "iec-61131-3":
                self.warn_output_never_driven = True
                self.warn_complexity = True
                self.warn_missing_else = True
            case "none":
                pass

    def apply_dialect_preset(self) -> None:
        if self.dialect not in ("rockwell", "iec-61131-3", "codesys"):
            valid = "rockwell, iec-61131-3, codesys"
            msg = f"Unknown dialect '{self.dialect}'. Valid: {valid}"
            raise ValueError(msg)

    def diagnostic_allowed(self, code: str) -> bool:
        match code:
            case "WC001":
                return self.warn_unused
            case "WR002" | "WS110":
                return self.warn_unreachable
            case "WR003":
                return self.warn_output_never_driven
            case "WR004":
                return self.warn_timer_pre
            case "WC005":
                return self.warn_shadowed
            case "WS101" | "WS102":
                return self.warn_numeric_hazards
            case "WS104" | "WS105":
                return self.warn_implicit_conversion
            case "WS107":
                return self.warn_missing_else
            case "WC103":
                return self.warn_complexity
            case _:
                return True

    def resolve_severity(self, code: str, default_severity: str) -> str:
        return self.severity_overrides.get(code, default_severity)


def apply_warning_toggles(
    config: LintConfig,
    *,
    disable: list[str] | None = None,
    enable: list[str] | None = None,
) -> None:
    for w in disable or []:
        w = w.strip()
        match w:
            case "unused":
                config.warn_unused = False
            case "unreachable":
                config.warn_unreachable = False
            case "output":
                config.warn_output_never_driven = False
            case "timer":
                config.warn_timer_pre = False
            case "shadowed":
                config.warn_shadowed = False
            case "numeric":
                config.warn_numeric_hazards = False
            case "complexity":
                config.warn_complexity = False
            case "conversion":
                config.warn_implicit_conversion = False
            case "missing-else":
                config.warn_missing_else = False
    for w in enable or []:
        w = w.strip()
        match w:
            case "numeric":
                config.warn_numeric_hazards = True
            case "complexity":
                config.warn_complexity = True


def apply_severity_overrides(
    config: LintConfig,
    overrides: list[str] | None = None,
) -> None:
    for ov in overrides or []:
        if "=" in ov:
            code, sev = ov.split("=", 1)
            config.severity_overrides[code.strip()] = sev.strip()
