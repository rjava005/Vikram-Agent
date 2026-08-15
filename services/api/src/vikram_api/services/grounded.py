from __future__ import annotations

import hashlib
from dataclasses import dataclass

from vikram_api.config import Settings
from vikram_api.domain.models import (
    Evidence,
    GroundingVerificationError,
    ModelAnswer,
    ModelClaim,
    ProviderInvalidResponseError,
    RemoteIndexLimitError,
    RetrievedEvidence,
)
from vikram_api.providers.hybrid import (
    HybridCandidate,
    RetrievalCandidate,
    lexical_rank,
    reciprocal_rank_fusion,
    semantic_rank,
)
from vikram_api.providers.nebius import (
    ClaimVerification,
    EvidenceExcerpt,
    GenerationResult,
    NebiusEmbeddingProvider,
    NebiusGroundedModelProvider,
    ProviderCallMetadata,
)
from vikram_api.repositories.sqlite import SqliteRepository

QUERY_INSTRUCTION = (
    "Instruct: Retrieve engineering evidence that directly answers the question.\nQuery: "
)


@dataclass(frozen=True)
class RemoteGroundedRun:
    answer: ModelAnswer
    retrieved: tuple[RetrievedEvidence, ...]
    candidates: tuple[HybridCandidate, ...]
    generation: ProviderCallMetadata
    verification: ProviderCallMetadata
    verification_outcomes: tuple[ClaimVerification, ...]

    @property
    def input_tokens(self) -> int | None:
        return _sum_optional(
            self.generation.usage.input_tokens,
            self.verification.usage.input_tokens,
        )

    @property
    def output_tokens(self) -> int | None:
        return _sum_optional(
            self.generation.usage.output_tokens,
            self.verification.usage.output_tokens,
        )


class RemoteGroundedPipeline:
    retrieval_strategy = "local-lexical-nebius-vector-rrf-v1"

    def __init__(
        self,
        *,
        settings: Settings,
        repository: SqliteRepository,
        embeddings: NebiusEmbeddingProvider,
        model: NebiusGroundedModelProvider,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.embeddings = embeddings
        self.model = model

    async def answer(
        self,
        project_id: str,
        question: str,
        evidence: list[Evidence],
        created_at: str,
        policy_revision: int,
    ) -> RemoteGroundedRun:
        if not evidence:
            raise GroundingVerificationError(
                "Import a source with extractable evidence before asking a remote question."
            )
        if len(evidence) > self.settings.nebius_max_evidence_units:
            raise RemoteIndexLimitError(
                "This project exceeds the temporary remote indexing limit. Narrow the sources or use local mode."
            )
        if any(len(item.content) > self.embeddings.max_input_characters for item in evidence):
            raise RemoteIndexLimitError(
                "An evidence unit exceeds the remote embedding character limit. Re-import it as smaller sections or use local mode."
            )
        query_text = f"{QUERY_INSTRUCTION}{question}"
        if len(query_text) > self.embeddings.max_input_characters:
            raise RemoteIndexLimitError(
                "The question exceeds the remote embedding character limit. Shorten it or use local mode."
            )

        self.repository.assert_nebius_policy(project_id, policy_revision)

        content_hashes = {
            item.id: hashlib.sha256(item.content.encode("utf-8")).hexdigest() for item in evidence
        }
        vectors = self.repository.get_cached_embeddings(
            project_id=project_id,
            provider_id=self.embeddings.provider_id,
            model_id=self.embeddings.model_id,
            expected_dimensions=self.embeddings.dimensions,
            content_hashes=content_hashes,
        )
        missing = [item for item in evidence if item.id not in vectors]
        if missing:
            self.repository.assert_nebius_policy(project_id, policy_revision)
            embedded = await self.embeddings.embed_batch([item.content for item in missing])
            if len(embedded.vectors) != len(missing):
                raise ProviderInvalidResponseError(
                    "The remote AI provider returned an incomplete embedding batch."
                )
            vectors.update(
                {item.id: vector for item, vector in zip(missing, embedded.vectors, strict=True)}
            )
            self.repository.store_embeddings(
                project_id=project_id,
                provider_id=self.embeddings.provider_id,
                model_id=self.embeddings.model_id,
                records=[(item.id, content_hashes[item.id], vectors[item.id]) for item in missing],
                expected_policy_revision=policy_revision,
                created_at=created_at,
            )

        self.repository.assert_nebius_policy(project_id, policy_revision)
        query_result = await self.embeddings.embed_batch([query_text])
        if len(query_result.vectors) != 1:
            raise ProviderInvalidResponseError(
                "The remote AI provider returned an invalid query embedding."
            )
        candidates = [
            RetrievalCandidate(
                evidence_id=item.id,
                text=item.content,
                embedding=vectors[item.id],
                metadata={
                    "source_id": item.source_id,
                    "source_version_id": item.source_version_id,
                },
            )
            for item in evidence
        ]
        fused = reciprocal_rank_fusion(
            lexical_rank(question, candidates),
            semantic_rank(query_result.vectors[0], candidates),
        )
        selected = fused[: self.settings.nebius_retrieval_limit]
        if not selected:
            raise GroundingVerificationError(
                "The imported sources did not provide enough relevant evidence for this question."
            )
        evidence_by_id = {item.id: item for item in evidence}
        selected_evidence = [evidence_by_id[item.evidence_id] for item in selected]
        excerpts = [
            EvidenceExcerpt(
                evidence_id=item.id,
                text=item.content[: self.settings.nebius_max_evidence_characters],
            )
            for item in selected_evidence
        ]

        generation = await self._generate_with_one_structured_retry(
            project_id, policy_revision, question, excerpts
        )
        if not generation.claims:
            raise GroundingVerificationError(
                "The remote model found insufficient evidence for a grounded answer."
            )
        self.repository.assert_nebius_policy(project_id, policy_revision)
        verification = await self.model.verify(generation, excerpts)
        supported_ids = set(verification.supported_claim_ids)
        supported_claims = tuple(
            ModelClaim(
                id=claim.claim_id,
                text=claim.text,
                evidence_ids=claim.evidence_ids,
            )
            for claim in generation.claims
            if claim.claim_id in supported_ids
        )
        if not supported_claims:
            raise GroundingVerificationError(
                "The proposed answer did not pass evidence verification and was not saved."
            )
        answer_text = "\n\n".join(claim.text for claim in supported_claims)
        scores = {item.evidence_id: item.fused_score for item in selected}
        retrieved = tuple(
            RetrievedEvidence(evidence=item, score=scores[item.id]) for item in selected_evidence
        )
        return RemoteGroundedRun(
            answer=ModelAnswer(text=answer_text, claims=supported_claims),
            retrieved=retrieved,
            candidates=tuple(fused),
            generation=generation.metadata,
            verification=verification.metadata,
            verification_outcomes=verification.outcomes,
        )

    async def _generate_with_one_structured_retry(
        self,
        project_id: str,
        policy_revision: int,
        question: str,
        evidence: list[EvidenceExcerpt],
    ) -> GenerationResult:
        self.repository.assert_nebius_policy(project_id, policy_revision)
        try:
            return await self.model.generate(question, evidence)
        except ProviderInvalidResponseError:
            self.repository.assert_nebius_policy(project_id, policy_revision)
            return await self.model.generate(question, evidence)


def _sum_optional(*values: int | None) -> int | None:
    known = [value for value in values if value is not None]
    return sum(known) if known else None
