from __future__ import annotations

import logging
import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


class ReviewType(str, Enum):
    QUALITY = "quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    DOCUMENTATION = "documentation"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# The model is asked for these exact values and mostly obliges, but it does reach for
# a neighbouring word often enough to matter — "error" as a *type* is the classic,
# because "error" is a severity here and the two fields sit next to each other. The
# finding behind such a comment is usually perfectly good, so a near miss is mapped
# onto the closest real value rather than thrown away with the comment attached to it.
TYPE_ALIASES: dict[str, ReviewType] = {
    "error": ReviewType.QUALITY,  # severity leaking into the type field
    "warning": ReviewType.QUALITY,
    "critical": ReviewType.QUALITY,
    "info": ReviewType.QUALITY,
    "bug": ReviewType.QUALITY,
    "correctness": ReviewType.QUALITY,
    "logic": ReviewType.QUALITY,
    "maintainability": ReviewType.QUALITY,
    "reliability": ReviewType.QUALITY,
    "error_handling": ReviewType.QUALITY,
    "complexity": ReviewType.QUALITY,
    "duplication": ReviewType.QUALITY,
    "security_vulnerability": ReviewType.SECURITY,
    "vulnerability": ReviewType.SECURITY,
    "safety": ReviewType.SECURITY,
    "sec": ReviewType.SECURITY,
    "perf": ReviewType.PERFORMANCE,
    "efficiency": ReviewType.PERFORMANCE,
    "scalability": ReviewType.PERFORMANCE,
    "readability": ReviewType.STYLE,
    "formatting": ReviewType.STYLE,
    "convention": ReviewType.STYLE,
    "conventions": ReviewType.STYLE,
    "naming": ReviewType.STYLE,
    "lint": ReviewType.STYLE,
    "docs": ReviewType.DOCUMENTATION,
    "doc": ReviewType.DOCUMENTATION,
    "comment": ReviewType.DOCUMENTATION,
    "comments": ReviewType.DOCUMENTATION,
}

SEVERITY_ALIASES: dict[str, Severity] = {
    "low": Severity.INFO,
    "minor": Severity.INFO,
    "nit": Severity.INFO,
    "note": Severity.INFO,
    "suggestion": Severity.INFO,
    "trivial": Severity.INFO,
    "medium": Severity.WARNING,
    "moderate": Severity.WARNING,
    "warn": Severity.WARNING,
    "high": Severity.ERROR,
    "major": Severity.ERROR,
    "severe": Severity.ERROR,
    "blocker": Severity.CRITICAL,
    "fatal": Severity.CRITICAL,
}


def _coerce_enum(value, enum, aliases, fallback, field):
    """Map a value the model invented onto the closest real enum member.

    Dropping the comment instead would lose a real finding over a wrong label, and
    failing would lose the whole file (see Analyzer._parse_response), so an unknown
    value degrades to ``fallback`` — loudly, because a recurring one is a prompt bug.
    """
    if isinstance(value, enum):
        return value

    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")

    try:
        return enum(text)
    except ValueError:
        pass

    if text in aliases:
        alias = aliases[text]
        logger.info("Review comment %s %r mapped to %r", field, value, alias.value)
        return alias

    logger.warning(
        "Review comment %s %r is not a %s; defaulting to %r",
        field, value, enum.__name__, fallback.value,
    )
    return fallback


class ReviewComment(BaseModel):
    file_path: str
    line: int | None = None
    type: ReviewType
    severity: Severity
    message: str
    suggestion: str | None = None

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, value):
        return _coerce_enum(value, ReviewType, TYPE_ALIASES, ReviewType.QUALITY, "type")

    @field_validator("severity", mode="before")
    @classmethod
    def _validate_severity(cls, value):
        # Defaults to WARNING rather than INFO: an unlabelled finding should not be
        # quietly filtered out by a repo whose min_severity is the default warning.
        return _coerce_enum(value, Severity, SEVERITY_ALIASES, Severity.WARNING, "severity")

    @field_validator("line", mode="before")
    @classmethod
    def _validate_line(cls, value):
        """A line is sometimes a range ("12-15") or "L12". Take the first number."""
        if value is None or isinstance(value, int):
            return value
        match = re.search(r"\d+", str(value))
        return int(match.group()) if match else None


class FileReviewResponse(BaseModel):
    # "ignore", not "forbid": an extra key the model decided to add (a "summary", a
    # "score") is not a reason to throw away every finding in the file.
    model_config = ConfigDict(extra="ignore")

    comments: list[ReviewComment] = Field(default_factory=list)
    positives: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

class ReviewResult(BaseModel):
    score: int = Field(ge=0, le=100)
    comments: list[ReviewComment] = Field(default_factory=list)
    positives: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    has_critical_issues: bool = False
    failed_files: list[str] = Field(default_factory=list)
    total_files: int = 0