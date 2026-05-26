from dataclasses import dataclass, field

from l5x_lint.domain.models import Location


@dataclass
class Diagnostic:
    code: str
    severity: str
    location: Location
    message: str
    hint: str | None = None
    fix_suggestion: str | None = None


@dataclass
class FixSuggestion:
    code: str
    description: str
    replacement: str | None = None
    target_tag: str | None = None


@dataclass
class AnalysisResult:
    passed: bool
    error_count: int
    warning_count: int
    diagnostics: list[Diagnostic] = field(default_factory=list)
