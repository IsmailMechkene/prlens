from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


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

class ReviewComment(BaseModel):
    file_path: str
    line: int | None = None
    type: ReviewType
    severity: Severity
    message: str
    suggestion: str | None = None

class FileReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

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