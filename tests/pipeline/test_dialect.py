from l5x_lint.domain.dialect import (
    DIALECT_PRESETS,
    DialectConfig,
    resolve_dialect,
)


def test_rockwell_preset():
    d = DIALECT_PRESETS["rockwell"]
    assert d.allow_keywords_case_insensitive
    assert d.allow_positional_args
    assert d.allow_jsr
    assert d.allow_wildcard_operands
    assert d.allow_type_punning
    assert d.allow_c_style_comments
    assert d.allow_cross_family_widening


def test_iec61131_preset():
    d = DIALECT_PRESETS["iec-61131-3"]
    assert not d.allow_keywords_case_insensitive
    assert not d.allow_positional_args
    assert not d.allow_jsr
    assert not d.allow_wildcard_operands
    assert not d.allow_type_punning
    assert not d.allow_c_style_comments
    assert not d.allow_cross_family_widening


def test_codesys_preset():
    d = DIALECT_PRESETS["codesys"]
    assert not d.allow_keywords_case_insensitive
    assert d.allow_positional_args
    assert not d.allow_jsr
    assert d.allow_wildcard_operands
    assert d.allow_type_punning
    assert d.allow_c_style_comments
    assert d.allow_cross_family_widening


def test_resolve_dialect():
    d = resolve_dialect("rockwell")
    assert d.name == "rockwell"
    assert d.allow_jsr
    d2 = resolve_dialect("iec-61131-3")
    assert d2.name == "iec-61131-3"
    assert not d2.allow_jsr


def test_resolve_unknown_dialect():
    try:
        resolve_dialect("nonexistent")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_dialect_config_defaults():
    d = DialectConfig()
    assert d.name == "rockwell"
    assert d.allow_keywords_case_insensitive
