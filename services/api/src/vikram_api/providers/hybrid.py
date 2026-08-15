from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

JsonScalar = str | int | float | bool | None

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+.-]*", re.IGNORECASE)
_STOP_WORDS = frozenset(
    {
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
)


@dataclass(frozen=True)
class RetrievalCandidate:
    """A local evidence candidate; text is intentionally absent from serialized metadata."""

    evidence_id: str
    text: str
    embedding: tuple[float, ...]
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id must not be empty")
        if any(not math.isfinite(value) for value in self.embedding):
            raise ValueError("candidate embeddings must contain only finite values")
        _validate_metadata(self.metadata)


@dataclass(frozen=True)
class RankedCandidate:
    evidence_id: str
    score: float
    rank: int
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "score": self.score,
            "rank": self.rank,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class HybridCandidate:
    evidence_id: str
    lexical_score: float | None
    semantic_score: float | None
    lexical_rank: int | None
    semantic_rank: int | None
    fused_score: float
    metadata: Mapping[str, JsonScalar] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        """Return JSON-serializable ranking metadata without private evidence text."""

        return {
            "evidence_id": self.evidence_id,
            "lexical_score": self.lexical_score,
            "semantic_score": self.semantic_score,
            "lexical_rank": self.lexical_rank,
            "semantic_rank": self.semantic_rank,
            "fused_score": self.fused_score,
            "metadata": dict(self.metadata),
        }


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Compute cosine similarity, returning zero when either vector has zero magnitude."""

    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    if any(not math.isfinite(value) for value in (*left, *right)):
        raise ValueError("embeddings must contain only finite values")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def lexical_rank(query: str, candidates: Sequence[RetrievalCandidate]) -> list[RankedCandidate]:
    """Rank positive token-overlap matches with evidence ID as the stable tie-break."""

    _candidate_index(candidates)
    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    scored = [
        (
            candidate,
            len(query_tokens & _tokens(candidate.text)) / len(query_tokens),
        )
        for candidate in candidates
    ]
    ordered = sorted(
        ((candidate, score) for candidate, score in scored if score > 0.0),
        key=lambda item: (-item[1], item[0].evidence_id),
    )
    return [
        RankedCandidate(
            evidence_id=candidate.evidence_id,
            score=round(score, 12),
            rank=index,
            metadata=candidate.metadata,
        )
        for index, (candidate, score) in enumerate(ordered, start=1)
    ]


def semantic_rank(
    query_embedding: Sequence[float], candidates: Sequence[RetrievalCandidate]
) -> list[RankedCandidate]:
    """Rank positive cosine matches with deterministic tie handling."""

    _candidate_index(candidates)
    scored = [
        (candidate, cosine_similarity(query_embedding, candidate.embedding))
        for candidate in candidates
    ]
    ordered = sorted(
        ((candidate, score) for candidate, score in scored if score > 0.0),
        key=lambda item: (-item[1], item[0].evidence_id),
    )
    return [
        RankedCandidate(
            evidence_id=candidate.evidence_id,
            score=round(score, 12),
            rank=index,
            metadata=candidate.metadata,
        )
        for index, (candidate, score) in enumerate(ordered, start=1)
    ]


def reciprocal_rank_fusion(
    lexical: Sequence[RankedCandidate],
    semantic: Sequence[RankedCandidate],
    *,
    rrf_k: int = 60,
    limit: int | None = None,
) -> list[HybridCandidate]:
    """Fuse lexical and semantic ranks using RRF and a stable evidence-ID tie-break."""

    if rrf_k < 1:
        raise ValueError("rrf_k must be positive")
    if limit is not None and limit < 0:
        raise ValueError("limit must not be negative")
    lexical_by_id = _ranking_index(lexical, "lexical")
    semantic_by_id = _ranking_index(semantic, "semantic")
    evidence_ids = lexical_by_id.keys() | semantic_by_id.keys()
    fused: list[HybridCandidate] = []
    for evidence_id in evidence_ids:
        lexical_item = lexical_by_id.get(evidence_id)
        semantic_item = semantic_by_id.get(evidence_id)
        if lexical_item is not None:
            metadata = lexical_item.metadata
        elif semantic_item is not None:
            metadata = semantic_item.metadata
        else:  # pragma: no cover - the ID came from one of these two mappings
            raise AssertionError("fused candidate has no source ranking")
        fused_score = sum(
            1.0 / (rrf_k + item.rank) for item in (lexical_item, semantic_item) if item is not None
        )
        fused.append(
            HybridCandidate(
                evidence_id=evidence_id,
                lexical_score=lexical_item.score if lexical_item else None,
                semantic_score=semantic_item.score if semantic_item else None,
                lexical_rank=lexical_item.rank if lexical_item else None,
                semantic_rank=semantic_item.rank if semantic_item else None,
                fused_score=round(fused_score, 12),
                metadata=metadata,
            )
        )
    fused.sort(key=lambda item: (-item.fused_score, item.evidence_id))
    return fused if limit is None else fused[:limit]


def hybrid_rank(
    query: str,
    query_embedding: Sequence[float],
    candidates: Sequence[RetrievalCandidate],
    *,
    rrf_k: int = 60,
    limit: int = 4,
) -> list[HybridCandidate]:
    """Run the separately inspectable lexical, semantic, and fusion stages."""

    if limit < 0:
        raise ValueError("limit must not be negative")
    return reciprocal_rank_fusion(
        lexical_rank(query, candidates),
        semantic_rank(query_embedding, candidates),
        rrf_k=rrf_k,
        limit=limit,
    )


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(text) if token.lower() not in _STOP_WORDS}


def _candidate_index(
    candidates: Sequence[RetrievalCandidate],
) -> dict[str, RetrievalCandidate]:
    indexed = {candidate.evidence_id: candidate for candidate in candidates}
    if len(indexed) != len(candidates):
        raise ValueError("candidate evidence IDs must be unique")
    return indexed


def _ranking_index(ranking: Sequence[RankedCandidate], label: str) -> dict[str, RankedCandidate]:
    indexed: dict[str, RankedCandidate] = {}
    ranks: set[int] = set()
    for item in ranking:
        if item.evidence_id in indexed:
            raise ValueError(f"{label} ranking contains a duplicate evidence ID")
        if item.rank < 1 or item.rank in ranks:
            raise ValueError(f"{label} ranking contains an invalid or duplicate rank")
        if not math.isfinite(item.score):
            raise ValueError(f"{label} ranking scores must be finite")
        _validate_metadata(item.metadata)
        indexed[item.evidence_id] = item
        ranks.add(item.rank)
    return indexed


def _validate_metadata(metadata: Mapping[str, JsonScalar]) -> None:
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise ValueError("candidate metadata keys must be strings")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("candidate metadata numbers must be finite")
