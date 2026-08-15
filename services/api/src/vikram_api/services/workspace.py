from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from vikram_api.config import Settings
from vikram_api.contracts import (
    AiMode,
    AiPolicyResponse,
    AiPolicyUpdate,
    AnswerProvenance,
    AnswerResponse,
    CitationResponse,
    ClaimResponse,
    FeedbackResponse,
    FeedbackStatus,
    FocusResponse,
    FocusStatus,
    FocusTransitionType,
    GroundingStatus,
    MarkdownLocator,
    PdfLocator,
    ProjectResponse,
    SourceKind,
    SourceResponse,
    TaskResponse,
    VerificationStatus,
    WorkspaceResponse,
)
from vikram_api.domain.models import (
    ConflictError,
    Evidence,
    ProviderNotConfiguredError,
    SourceTooLargeError,
    UnprocessableSourceError,
    UnsupportedSourceError,
    ZdrAttestationRequiredError,
)
from vikram_api.providers.interfaces import (
    BlobStorageProvider,
    Clock,
    DocumentParser,
    EmbeddingProvider,
    ModelProvider,
    RetrievalProvider,
    SpeechToTextProvider,
    TextToSpeechProvider,
)
from vikram_api.providers.parsers import MarkdownParser, PdfParser
from vikram_api.repositories.sqlite import SqliteRepository
from vikram_api.services.grounded import RemoteGroundedPipeline


def as_utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


class VikramService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: SqliteRepository,
        storage: BlobStorageProvider,
        model: ModelProvider,
        embeddings: EmbeddingProvider,
        retrieval: RetrievalProvider,
        speech_to_text: SpeechToTextProvider,
        text_to_speech: TextToSpeechProvider,
        clock: Clock,
        remote_grounding: RemoteGroundedPipeline | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.storage = storage
        self.model = model
        self.embeddings = embeddings
        self.retrieval = retrieval
        self.speech_to_text = speech_to_text
        self.text_to_speech = text_to_speech
        self.clock = clock
        self.remote_grounding = remote_grounding
        self._active_remote_runs: dict[str, set[asyncio.Task[object]]] = {}
        self._policy_cancelled_runs: set[asyncio.Task[object]] = set()

    def create_project(self, name: str) -> ProjectResponse:
        normalized = " ".join(name.split())
        record = self.repository.create_project(
            str(uuid4()), normalized, as_utc_text(self.clock.now())
        )
        return ProjectResponse.model_validate(record)

    def list_projects(self) -> list[ProjectResponse]:
        return [ProjectResponse.model_validate(row) for row in self.repository.list_projects()]

    def get_workspace(self, project_id: str) -> WorkspaceResponse:
        project = ProjectResponse.model_validate(self.repository.get_project(project_id))
        ai_policy = AiPolicyResponse.model_validate(self.repository.get_ai_policy(project_id))
        sources = [
            SourceResponse.model_validate(row) for row in self.repository.list_sources(project_id)
        ]
        tasks = [TaskResponse.model_validate(row) for row in self.repository.list_tasks(project_id)]
        focus = self.repository.get_active_focus_for_project(project_id)
        return WorkspaceResponse(
            project=project,
            ai_policy=ai_policy,
            sources=sources,
            tasks=tasks,
            active_focus=self._focus_response(focus) if focus else None,
        )

    async def set_ai_policy(self, project_id: str, update: AiPolicyUpdate) -> AiPolicyResponse:
        self.repository.get_project(project_id)
        if update.mode is AiMode.NEBIUS:
            if not update.zdr_attested:
                raise ZdrAttestationRequiredError(
                    "Attest that Zero Data Retention is enabled before sending project data to Nebius."
                )
            if not self.settings.remote_ai_configured:
                raise ProviderNotConfiguredError(
                    "Start the API in Nebius mode with a local NEBIUS_API_KEY first."
                )
        record = self.repository.update_ai_policy(
            project_id=project_id,
            mode=update.mode.value,
            zdr_attested=update.zdr_attested if update.mode is AiMode.NEBIUS else False,
            expected_revision=update.expected_revision,
            updated_at=as_utc_text(self.clock.now()),
        )
        if update.mode is AiMode.LOCAL:
            await self._cancel_remote_runs(project_id)
        return AiPolicyResponse.model_validate(record)

    def import_source(
        self, project_id: str, filename: str, media_type: str | None, content: bytes
    ) -> SourceResponse:
        self.repository.get_project(project_id)
        if len(content) > self.settings.max_source_bytes:
            raise SourceTooLargeError(
                f"Source exceeds the {self.settings.max_source_bytes // (1024 * 1024)} MB limit."
            )
        suffix = Path(filename).suffix.lower()
        kind: SourceKind
        parser: DocumentParser
        if suffix == ".md" and media_type in {
            None,
            "text/markdown",
            "text/plain",
            "application/octet-stream",
        }:
            kind, parser = SourceKind.MARKDOWN, MarkdownParser()
        elif suffix == ".pdf" and media_type in {
            None,
            "application/pdf",
            "application/octet-stream",
        }:
            kind, parser = SourceKind.PDF, PdfParser()
        else:
            raise UnsupportedSourceError("Choose one .pdf or .md engineering source.")
        parsed = parser.parse(content)
        if not parsed:
            raise UnprocessableSourceError("The source contains no extractable evidence.")
        now = as_utc_text(self.clock.now())
        storage_key = self.storage.put(content, self.settings.provider_timeout_seconds)
        source_id, version_id = str(uuid4()), str(uuid4())
        evidence_rows: list[tuple[str, int, str, str, str]] = [
            (
                str(uuid4()),
                item.ordinal,
                item.content,
                item.locator_kind,
                json.dumps(item.locator, separators=(",", ":"), sort_keys=True),
            )
            for item in parsed
        ]
        record = self.repository.create_source(
            source_id=source_id,
            version_id=version_id,
            project_id=project_id,
            name=Path(filename).name,
            kind=kind.value,
            sha256=hashlib.sha256(content).hexdigest(),
            storage_key=storage_key,
            parser_id=parser.parser_id,
            evidence=evidence_rows,
            created_at=now,
        )
        return SourceResponse.model_validate(record)

    async def answer(self, project_id: str, question: str) -> AnswerResponse:
        policy = AiPolicyResponse.model_validate(self.repository.get_ai_policy(project_id))
        if policy.mode is AiMode.NEBIUS:
            if self.remote_grounding is None or not self.settings.remote_ai_configured:
                raise ProviderNotConfiguredError(
                    "Remote AI is enabled for this project but is not configured in the API."
                )
            return await self._answer_remote(project_id, question, policy.revision)
        return self._answer_local(project_id, question)

    def _answer_local(self, project_id: str, question: str) -> AnswerResponse:
        self.repository.get_project(project_id)
        evidence = self.repository.list_evidence(project_id)
        retrieved = self.retrieval.search(
            question, evidence, self.embeddings, self.settings.provider_timeout_seconds
        )
        generated = self.model.answer(question, retrieved, self.settings.provider_timeout_seconds)
        allowed = {candidate.evidence.id: candidate.evidence for candidate in retrieved}
        for claim in generated.claims:
            if not claim.evidence_ids or any(item not in allowed for item in claim.evidence_ids):
                raise UnprocessableSourceError("The answer provider returned an invalid citation.")
        answer_id = str(uuid4())
        created_at_value = self.clock.now()
        grounding = (
            GroundingStatus.GROUNDED if generated.claims else GroundingStatus.INSUFFICIENT_EVIDENCE
        )
        claims = [
            ClaimResponse(id=claim.id, text=claim.text, evidence_ids=list(claim.evidence_ids))
            for claim in generated.claims
        ]
        citations: list[CitationResponse] = []
        citation_records: list[dict[str, Any]] = []
        ordinal = 0
        for claim in generated.claims:
            for evidence_id in claim.evidence_ids:
                item = allowed[evidence_id]
                citation_id = str(uuid4())
                excerpt = " ".join(item.content.split())[:320]
                citations.append(
                    CitationResponse(
                        id=citation_id,
                        evidence_id=item.id,
                        source_id=item.source_id,
                        source_version_id=item.source_version_id,
                        source_name=item.source_name,
                        locator=self._locator(item),
                        excerpt=excerpt,
                        supported_claim_ids=[claim.id],
                    )
                )
                citation_records.append(
                    {
                        "id": citation_id,
                        "answer_id": answer_id,
                        "evidence_id": item.id,
                        "ordinal": ordinal,
                        "excerpt": excerpt,
                        "claim_id": claim.id,
                    }
                )
                ordinal += 1
        response = AnswerResponse(
            id=answer_id,
            project_id=project_id,
            question=question,
            text=generated.text,
            grounding=grounding,
            claims=claims,
            citations=citations,
            provider_id=self.model.provider_id,
            prompt_version=self.model.prompt_version,
            provenance=AnswerProvenance(
                provider_mode="fake",
                verification=VerificationStatus.LOCAL_DETERMINISTIC,
                model_id=self.model.provider_id,
                embedding_model_id=self.embeddings.provider_id,
                retrieval_strategy=self.retrieval.provider_id,
                candidate_count=len(retrieved),
                selected_evidence_count=len(allowed),
            ),
            created_at=created_at_value,
        )
        self.repository.create_answer(
            answer=response.model_dump(mode="json"),
            citations=citation_records,
            answer_run={
                "answer_id": answer_id,
                "provider_mode": "fake",
                "model_id": self.model.provider_id,
                "embedding_model_id": self.embeddings.provider_id,
                "retrieval_strategy": self.retrieval.provider_id,
                "verifier_model_id": None,
                "verifier_prompt_version": None,
                "candidate_count": len(retrieved),
                "selected_evidence_count": len(allowed),
                "generation_latency_ms": None,
                "verification_latency_ms": None,
                "input_tokens": None,
                "output_tokens": None,
                "created_at": as_utc_text(created_at_value),
            },
            retrieval_candidates=[
                {
                    "answer_id": answer_id,
                    "evidence_id": candidate.evidence.id,
                    "lexical_rank": None,
                    "semantic_rank": None,
                    "fused_score": candidate.score,
                    "selected": 1,
                }
                for candidate in retrieved
            ],
            claim_verifications=[
                {
                    "answer_id": answer_id,
                    "claim_id": claim.id,
                    "evidence_ids_json": json.dumps(list(claim.evidence_ids)),
                    "verdict": "supported",
                    "reason": "Deterministic provider citation IDs passed structural validation.",
                    "created_at": as_utc_text(created_at_value),
                }
                for claim in generated.claims
            ],
        )
        return response

    async def _answer_remote(
        self, project_id: str, question: str, policy_revision: int
    ) -> AnswerResponse:
        if self.remote_grounding is None:
            raise ProviderNotConfiguredError("Remote AI is not configured in the API.")
        current_task = asyncio.current_task()
        if current_task is None:
            raise RuntimeError("Remote answers require an active asyncio task.")
        active = self._active_remote_runs.setdefault(project_id, set())
        active.add(current_task)
        try:
            self.repository.get_project(project_id)
            evidence = self.repository.list_evidence(project_id)
            created_at_value = self.clock.now()
            run = await self.remote_grounding.answer(
                project_id,
                question,
                evidence,
                as_utc_text(created_at_value),
                policy_revision,
            )
        except asyncio.CancelledError:
            if current_task in self._policy_cancelled_runs:
                raise ConflictError(
                    "Remote AI was revoked while the answer was running; no result was saved."
                ) from None
            raise
        finally:
            self._policy_cancelled_runs.discard(current_task)
            active.discard(current_task)
            if not active:
                self._active_remote_runs.pop(project_id, None)
        allowed = {candidate.evidence.id: candidate.evidence for candidate in run.retrieved}
        for claim in run.answer.claims:
            if not claim.evidence_ids or any(item not in allowed for item in claim.evidence_ids):
                raise UnprocessableSourceError("The verified answer contained an invalid citation.")
        answer_id = str(uuid4())
        claims = [
            ClaimResponse(id=claim.id, text=claim.text, evidence_ids=list(claim.evidence_ids))
            for claim in run.answer.claims
        ]
        citations: list[CitationResponse] = []
        citation_records: list[dict[str, Any]] = []
        ordinal = 0
        for claim in run.answer.claims:
            for evidence_id in claim.evidence_ids:
                item = allowed[evidence_id]
                citation_id = str(uuid4())
                excerpt = " ".join(item.content.split())[:320]
                citations.append(
                    CitationResponse(
                        id=citation_id,
                        evidence_id=item.id,
                        source_id=item.source_id,
                        source_version_id=item.source_version_id,
                        source_name=item.source_name,
                        locator=self._locator(item),
                        excerpt=excerpt,
                        supported_claim_ids=[claim.id],
                    )
                )
                citation_records.append(
                    {
                        "id": citation_id,
                        "answer_id": answer_id,
                        "evidence_id": item.id,
                        "ordinal": ordinal,
                        "excerpt": excerpt,
                        "claim_id": claim.id,
                    }
                )
                ordinal += 1
        response = AnswerResponse(
            id=answer_id,
            project_id=project_id,
            question=question,
            text=run.answer.text,
            grounding=GroundingStatus.GROUNDED,
            claims=claims,
            citations=citations,
            provider_id=run.generation.provider_id,
            prompt_version=run.generation.prompt_version
            or self.remote_grounding.model.prompt_version,
            provenance=AnswerProvenance(
                provider_mode="nebius",
                verification=VerificationStatus.REMOTE_VERIFIED,
                model_id=run.generation.model_id,
                embedding_model_id=self.remote_grounding.embeddings.model_id,
                retrieval_strategy=self.remote_grounding.retrieval_strategy,
                verifier_model_id=run.verification.model_id,
                verifier_prompt_version=run.verification.prompt_version,
                candidate_count=len(run.candidates),
                selected_evidence_count=len(run.retrieved),
                generation_latency_ms=run.generation.latency_ms,
                verification_latency_ms=run.verification.latency_ms,
            ),
            created_at=created_at_value,
        )
        selected_ids = {item.evidence.id for item in run.retrieved}
        self.repository.create_answer(
            answer=response.model_dump(mode="json"),
            citations=citation_records,
            answer_run={
                "answer_id": answer_id,
                "provider_mode": "nebius",
                "model_id": run.generation.model_id,
                "embedding_model_id": self.remote_grounding.embeddings.model_id,
                "retrieval_strategy": self.remote_grounding.retrieval_strategy,
                "verifier_model_id": run.verification.model_id,
                "verifier_prompt_version": run.verification.prompt_version,
                "candidate_count": len(run.candidates),
                "selected_evidence_count": len(run.retrieved),
                "generation_latency_ms": run.generation.latency_ms,
                "verification_latency_ms": run.verification.latency_ms,
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "created_at": as_utc_text(created_at_value),
            },
            retrieval_candidates=[
                {
                    "answer_id": answer_id,
                    "evidence_id": candidate.evidence_id,
                    "lexical_rank": candidate.lexical_rank,
                    "semantic_rank": candidate.semantic_rank,
                    "fused_score": candidate.fused_score,
                    "selected": int(candidate.evidence_id in selected_ids),
                }
                for candidate in run.candidates
            ],
            claim_verifications=[
                {
                    "answer_id": answer_id,
                    "claim_id": outcome.claim_id,
                    "evidence_ids_json": json.dumps(list(outcome.evidence_ids)),
                    "verdict": outcome.verdict,
                    "reason": f"Remote verifier marked this claim {outcome.verdict}.",
                    "created_at": as_utc_text(created_at_value),
                }
                for outcome in run.verification_outcomes
            ],
            expected_ai_policy_revision=policy_revision,
        )
        return response

    async def _cancel_remote_runs(self, project_id: str) -> None:
        tasks = tuple(self._active_remote_runs.get(project_id, ()))
        current_task = asyncio.current_task()
        cancellable = tuple(task for task in tasks if task is not current_task and not task.done())
        self._policy_cancelled_runs.update(cancellable)
        for task in cancellable:
            task.cancel()
        if cancellable:
            await asyncio.gather(*cancellable, return_exceptions=True)

    def set_feedback(self, answer_id: str, status: FeedbackStatus) -> FeedbackResponse:
        record = self.repository.upsert_feedback(
            observation_id=str(uuid4()),
            answer_id=answer_id,
            status=status.value,
            now=as_utc_text(self.clock.now()),
        )
        return FeedbackResponse.model_validate(record)

    def task_from_answer(self, answer_id: str, requested_title: str | None) -> TaskResponse:
        answer = self.repository.get_answer_record(answer_id)
        title = " ".join((requested_title or f"Review: {answer['question']}").split())[:240]
        record = self.repository.create_task_from_answer(
            task_id=str(uuid4()),
            answer_id=answer_id,
            title=title,
            created_at=as_utc_text(self.clock.now()),
        )
        return TaskResponse.model_validate(record)

    def start_focus(self, task_id: str, duration_minutes: int) -> FocusResponse:
        record = self.repository.create_focus(
            focus_id=str(uuid4()),
            task_id=task_id,
            duration_seconds=duration_minutes * 60,
            now=as_utc_text(self.clock.now()),
        )
        return self._focus_response(record)

    def transition_focus(
        self, focus_id: str, transition: FocusTransitionType, expected_revision: int
    ) -> FocusResponse:
        record = self.repository.get_focus(focus_id)
        if record["revision"] != expected_revision:
            raise ConflictError("Focus session changed; refresh before retrying.")
        now = self.clock.now()
        elapsed = int(record["elapsed_active_seconds"])
        status = FocusStatus(record["status"])
        segment_start = self._parse_datetime(record["current_segment_started_at"])
        if transition is FocusTransitionType.PAUSE and status is FocusStatus.ACTIVE:
            if segment_start:
                elapsed += max(0, int((now - segment_start).total_seconds()))
            next_status, next_segment, completed_at = "paused", None, None
        elif transition is FocusTransitionType.RESUME and status is FocusStatus.PAUSED:
            next_status, next_segment, completed_at = "active", as_utc_text(now), None
        elif transition is FocusTransitionType.COMPLETE and status in {
            FocusStatus.ACTIVE,
            FocusStatus.PAUSED,
        }:
            if status is FocusStatus.ACTIVE and segment_start:
                elapsed += max(0, int((now - segment_start).total_seconds()))
            next_status, next_segment, completed_at = "completed", None, as_utc_text(now)
        else:
            raise ConflictError(f"Cannot {transition.value} a {status.value} focus session.")
        updated = self.repository.transition_focus(
            focus_id=focus_id,
            expected_revision=expected_revision,
            status=next_status,
            elapsed_seconds=elapsed,
            segment_started_at=next_segment,
            completed_at=completed_at,
            transition=transition.value,
            now=as_utc_text(now),
        )
        return self._focus_response(updated)

    def get_focus(self, focus_id: str) -> FocusResponse:
        return self._focus_response(self.repository.get_focus(focus_id))

    def _focus_response(self, record: dict[str, Any]) -> FocusResponse:
        elapsed = int(record["elapsed_active_seconds"])
        if record["status"] == "active" and record["current_segment_started_at"]:
            started = self._parse_datetime(record["current_segment_started_at"])
            if started:
                elapsed += max(0, int((self.clock.now() - started).total_seconds()))
        return FocusResponse(
            id=record["id"],
            task_id=record["task_id"],
            status=record["status"],
            duration_seconds=record["duration_seconds"],
            elapsed_active_seconds=elapsed,
            remaining_seconds=max(0, int(record["duration_seconds"]) - elapsed),
            current_segment_started_at=record["current_segment_started_at"],
            revision=record["revision"],
            created_at=record["created_at"],
            completed_at=record["completed_at"],
        )

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None

    @staticmethod
    def _locator(evidence: Evidence) -> PdfLocator | MarkdownLocator:
        if evidence.locator_kind == "pdf_page":
            return PdfLocator.model_validate(evidence.locator)
        return MarkdownLocator.model_validate(evidence.locator)
