from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

from vikram_api.domain.models import Evidence, ModelAnswer, ModelClaim, RetrievedEvidence
from vikram_api.providers.interfaces import EmbeddingProvider

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+-]*", re.IGNORECASE)
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "does",
    "explain",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "source",
    "the",
    "this",
    "to",
    "what",
    "why",
}


def tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOP_WORDS}


class DeterministicEmbeddingProvider:
    provider_id = "fake-hash-embedding-v1"
    dimensions = 32

    def embed(self, text: str, timeout_seconds: float) -> tuple[float, ...]:
        del timeout_seconds
        vector = [0.0] * self.dimensions
        for token in sorted(tokens(text)):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            vector[index] += 1.0 if digest[2] % 2 == 0 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return tuple(value / norm for value in vector)


class DeterministicRetrievalProvider:
    provider_id = "fake-hybrid-retrieval-v1"

    def search(
        self,
        question: str,
        evidence: Sequence[Evidence],
        embedding_provider: EmbeddingProvider,
        timeout_seconds: float,
        limit: int = 4,
    ) -> list[RetrievedEvidence]:
        query_tokens = tokens(question)
        query_vector = embedding_provider.embed(question, timeout_seconds)
        ranked: list[RetrievedEvidence] = []
        for item in evidence:
            item_tokens = tokens(item.content)
            lexical = len(query_tokens & item_tokens) / max(len(query_tokens), 1)
            item_vector = embedding_provider.embed(item.content, timeout_seconds)
            semantic = max(sum(a * b for a, b in zip(query_vector, item_vector, strict=True)), 0.0)
            score = round((0.75 * lexical) + (0.25 * semantic), 8) if lexical > 0 else 0.0
            ranked.append(RetrievedEvidence(evidence=item, score=score))
        ranked.sort(key=lambda candidate: (-candidate.score, candidate.evidence.id))
        return [candidate for candidate in ranked[:limit] if candidate.score > 0]


class DeterministicModelProvider:
    provider_id = "fake-extractive-model-v1"
    prompt_version = "grounded-answer-v1"

    def answer(
        self, question: str, evidence: Sequence[RetrievedEvidence], timeout_seconds: float
    ) -> ModelAnswer:
        del question, timeout_seconds
        if not evidence:
            return ModelAnswer(
                text="I could not find supporting evidence in the imported source.", claims=()
            )
        selected = evidence[0].evidence
        compact = " ".join(selected.content.split())
        excerpt = compact[:420].rstrip()
        if len(compact) > len(excerpt):
            excerpt += "…"
        claim = ModelClaim(id="claim-1", text=excerpt, evidence_ids=(selected.id,))
        return ModelAnswer(text=f"The source states: {excerpt}", claims=(claim,))


class DeterministicSpeechToTextProvider:
    provider_id = "fake-stt-v1"

    def transcribe(self, audio: bytes, timeout_seconds: float) -> str:
        del audio, timeout_seconds
        return "What does the imported source explain?"


class DeterministicTextToSpeechProvider:
    provider_id = "fake-tts-v1"

    def synthesize(self, text: str, timeout_seconds: float) -> bytes:
        del timeout_seconds
        return b"FAKE-WAV\x00" + hashlib.sha256(text.encode("utf-8")).digest()
