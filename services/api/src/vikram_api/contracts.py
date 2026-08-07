from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceKind(StrEnum):
    PDF = "pdf"
    MARKDOWN = "markdown"


class FeedbackStatus(StrEnum):
    UNDERSTOOD = "understood"
    UNCLEAR = "unclear"
    REVIEW_LATER = "review_later"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class FocusStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class GroundingStatus(StrEnum):
    GROUNDED = "grounded"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value


class ProjectResponse(ApiModel):
    id: str
    name: str
    created_at: datetime


class SourceResponse(ApiModel):
    id: str
    project_id: str
    version_id: str
    name: str
    kind: SourceKind
    status: Literal["ready", "failed"]
    evidence_count: int = Field(ge=0)
    created_at: datetime


class PdfLocator(ApiModel):
    kind: Literal["pdf_page"] = "pdf_page"
    page: int = Field(ge=1)


class MarkdownLocator(ApiModel):
    kind: Literal["markdown_section"] = "markdown_section"
    heading: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)


EvidenceLocator = Annotated[PdfLocator | MarkdownLocator, Field(discriminator="kind")]


class ClaimResponse(ApiModel):
    id: str
    text: str
    evidence_ids: list[str]


class CitationResponse(ApiModel):
    id: str
    evidence_id: str
    source_id: str
    source_version_id: str
    source_name: str
    locator: EvidenceLocator
    excerpt: str
    supported_claim_ids: list[str]


class AnswerCreate(ApiModel):
    question: str = Field(min_length=2, max_length=2000)

    @field_validator("question", mode="before")
    @classmethod
    def normalize_question(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value


class AnswerResponse(ApiModel):
    id: str
    project_id: str
    question: str
    text: str
    grounding: GroundingStatus
    claims: list[ClaimResponse]
    citations: list[CitationResponse]
    provider_id: str
    prompt_version: str
    created_at: datetime


class FeedbackUpdate(ApiModel):
    status: FeedbackStatus


class FeedbackResponse(ApiModel):
    id: str
    answer_id: str
    status: FeedbackStatus
    created_at: datetime
    updated_at: datetime


class TaskFromAnswerCreate(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value


class TaskResponse(ApiModel):
    id: str
    project_id: str
    source_answer_id: str | None
    title: str
    status: TaskStatus
    created_at: datetime
    completed_at: datetime | None


class FocusCreate(ApiModel):
    duration_minutes: int = Field(default=25, ge=1, le=240)


class FocusTransitionType(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    COMPLETE = "complete"


class FocusTransition(ApiModel):
    transition: FocusTransitionType
    expected_revision: int = Field(ge=0)


class FocusResponse(ApiModel):
    id: str
    task_id: str
    status: FocusStatus
    duration_seconds: int
    elapsed_active_seconds: int
    remaining_seconds: int
    current_segment_started_at: datetime | None
    revision: int
    created_at: datetime
    completed_at: datetime | None


class WorkspaceResponse(ApiModel):
    project: ProjectResponse
    sources: list[SourceResponse]
    tasks: list[TaskResponse]
    active_focus: FocusResponse | None


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    api_version: Literal["v1"] = "v1"
    provider_mode: str
    persistence: Literal["sqlite"] = "sqlite"


class ProblemResponse(ApiModel):
    type: str
    title: str
    status: int
    detail: str
