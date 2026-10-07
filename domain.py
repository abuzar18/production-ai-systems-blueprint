from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WorkflowStatus(str, Enum):
    VERIFIED = "verified"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class SourceDocument:
    source_id: str
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class Citation:
    source_id: str
    title: str
    score: float


@dataclass(slots=True)
class WorkflowResult:
    request_id: str
    status: WorkflowStatus
    answer: str
    citations: list[Citation] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)

