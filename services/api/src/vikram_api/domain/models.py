from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal


@dataclass(frozen=True)
class ParsedEvidence:
    ordinal: int
    content: str
    locator_kind: Literal["pdf_page", "markdown_section"]
    locator: dict[str, object]


@dataclass(frozen=True)
class Evidence:
    id: str
    source_id: str
    source_version_id: str
    source_name: str
    content: str
    locator_kind: Literal["pdf_page", "markdown_section"]
    locator: dict[str, object]


@dataclass(frozen=True)
class RetrievedEvidence:
    evidence: Evidence
    score: float


@dataclass(frozen=True)
class ModelClaim:
    id: str
    text: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ModelAnswer:
    text: str
    claims: tuple[ModelClaim, ...]


class DomainError(Exception):
    status_code = 400
    title = "Domain error"
    problem_type = "https://vikram.local/problems/domain-error"
    code = "domain_error"
    retryable = False


class NotFoundError(DomainError):
    status_code = 404
    title = "Not found"
    problem_type = "https://vikram.local/problems/not-found"
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    title = "Conflict"
    problem_type = "https://vikram.local/problems/conflict"
    code = "conflict"


class UnsupportedSourceError(DomainError):
    status_code = 415
    title = "Unsupported source"
    problem_type = "https://vikram.local/problems/unsupported-source"
    code = "unsupported_source"


class SourceTooLargeError(DomainError):
    status_code = 413
    title = "Source too large"
    problem_type = "https://vikram.local/problems/source-too-large"
    code = "source_too_large"


class UnprocessableSourceError(DomainError):
    status_code = 422
    title = "Source could not be parsed"
    problem_type = "https://vikram.local/problems/unprocessable-source"
    code = "unprocessable_source"


class ProviderNotConfiguredError(DomainError):
    status_code = 409
    title = "Remote AI is not configured"
    problem_type = "https://vikram.local/problems/provider-not-configured"
    code = "provider_not_configured"


class ZdrAttestationRequiredError(DomainError):
    status_code = 422
    title = "Zero Data Retention attestation required"
    problem_type = "https://vikram.local/problems/zdr-attestation-required"
    code = "zdr_attestation_required"


def utc_now() -> datetime:
    return datetime.now(UTC)
