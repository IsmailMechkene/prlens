from enum import Enum
from pydantic import BaseModel, Field


class PRStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"

class FileChangeStatus(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    RENAMED = "renamed"

class FileChange(BaseModel):
    filename: str
    status: FileChangeStatus
    additions: int
    deletions: int
    changes: int
    patch: str | None = None


class PR(BaseModel):
    title: str
    author: str
    body: str | None = None

    number: int
    repo: str

    status: PRStatus

    source_branch: str
    target_branch: str

    labels: list[str] = Field(default_factory=list)
    reviewers: list[str] = Field(default_factory=list)

    files: list[FileChange] = Field(default_factory=list)