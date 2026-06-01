from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DialectConfig:
    name: str = "rockwell"
    allow_keywords_case_insensitive: bool = True
    allow_positional_args: bool = True
    allow_jsr: bool = True
    allow_wildcard_operands: bool = True
    allow_type_punning: bool = True
    allow_c_style_comments: bool = True
    allow_cross_family_widening: bool = True


DIALECT_PRESETS: dict[str, DialectConfig] = {
    "rockwell": DialectConfig(
        name="rockwell",
        allow_keywords_case_insensitive=True,
        allow_positional_args=True,
        allow_jsr=True,
        allow_wildcard_operands=True,
        allow_type_punning=True,
        allow_c_style_comments=True,
        allow_cross_family_widening=True,
    ),
    "iec-61131-3": DialectConfig(
        name="iec-61131-3",
        allow_keywords_case_insensitive=False,
        allow_positional_args=False,
        allow_jsr=False,
        allow_wildcard_operands=False,
        allow_type_punning=False,
        allow_c_style_comments=False,
        allow_cross_family_widening=False,
    ),
    "codesys": DialectConfig(
        name="codesys",
        allow_keywords_case_insensitive=False,
        allow_positional_args=True,
        allow_jsr=False,
        allow_wildcard_operands=True,
        allow_type_punning=True,
        allow_c_style_comments=True,
        allow_cross_family_widening=True,
    ),
}


def resolve_dialect(name: str) -> DialectConfig:
    if name in DIALECT_PRESETS:
        return DIALECT_PRESETS[name]
    valid = ", ".join(sorted(DIALECT_PRESETS))
    msg = f"Unknown dialect '{name}'. Valid: {valid}"
    raise ValueError(msg)
