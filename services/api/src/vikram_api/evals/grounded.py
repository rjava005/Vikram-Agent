from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vikram_api.config import Settings
from vikram_api.domain.models import DomainError, ProviderInvalidResponseError
from vikram_api.providers.hybrid import RetrievalCandidate, hybrid_rank
from vikram_api.providers.nebius import (
    GENERATION_PROMPT_VERSION,
    VERIFICATION_PROMPT_VERSION,
    EvidenceExcerpt,
    NebiusEmbeddingProvider,
    NebiusGroundedModelProvider,
    NebiusHttpClient,
)


class EvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvalEvidence(EvalModel):
    id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=24_000)


class EvalCase(EvalModel):
    id: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=2, max_length=2_000)
    answerable: bool
    relevant_evidence_ids: list[str]


class EvalFixture(EvalModel):
    version: Literal[1]
    evidence: list[EvalEvidence]
    cases: list[EvalCase]

    @model_validator(mode="after")
    def validate_fixture(self) -> EvalFixture:
        evidence_ids = [item.id for item in self.evidence]
        case_ids = [item.id for item in self.cases]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evaluation evidence IDs must be unique")
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("evaluation case IDs must be unique")
        known = set(evidence_ids)
        for case in self.cases:
            if case.answerable != bool(case.relevant_evidence_ids):
                raise ValueError("answerable cases need evidence and negative cases must not")
            if any(item not in known for item in case.relevant_evidence_ids):
                raise ValueError("evaluation case references unknown evidence")
        return self


@dataclass(frozen=True)
class CaseResult:
    id: str
    answerable: bool
    retrieved_evidence_ids: list[str]
    retrieval_hit: bool
    grounded_success: bool
    negative_success: bool
    emitted_claims: int
    valid_verified_claims: int
    error_code: str | None = None


def load_fixture(path: Path) -> EvalFixture:
    return EvalFixture.model_validate_json(path.read_text(encoding="utf-8"))


def validate_fixture_threshold_shape(fixture: EvalFixture) -> None:
    answerable = sum(case.answerable for case in fixture.cases)
    negative = len(fixture.cases) - answerable
    if answerable < 12 or negative < 4:
        raise ValueError("grounded evaluation requires at least 12 answerable and 4 negative cases")


async def run_live(
    fixture: EvalFixture,
    settings: Settings,
    *,
    zdr_attested: bool,
    benchmark_permission_attested: bool,
) -> dict[str, object]:
    require_live_attestations(
        zdr_attested=zdr_attested,
        benchmark_permission_attested=benchmark_permission_attested,
    )
    if not settings.nebius_api_key:
        raise RuntimeError("Set NEBIUS_API_KEY locally before running the live evaluation.")
    client = NebiusHttpClient(
        api_key=settings.nebius_api_key,
        timeout_seconds=settings.nebius_timeout_seconds,
    )
    embeddings = NebiusEmbeddingProvider(
        client,
        model_id=settings.nebius_embedding_model,
        dimensions=settings.nebius_embedding_dimensions,
        max_batch_size=settings.nebius_embedding_batch_size,
        max_input_characters=settings.nebius_max_evidence_characters,
    )
    model = NebiusGroundedModelProvider(
        client,
        generation_model_id=settings.nebius_generation_model,
        max_evidence_items=settings.nebius_retrieval_limit,
        max_evidence_characters=settings.nebius_max_evidence_characters,
    )
    try:
        catalog = await client.get_json("/models", {"verbose": "true"})
        model_metadata = _required_model_metadata(
            catalog,
            {settings.nebius_generation_model, settings.nebius_embedding_model},
        )
        document_vectors = await embeddings.embed_batch([item.text for item in fixture.evidence])
        if len(document_vectors.vectors) != len(fixture.evidence):
            raise ProviderInvalidResponseError(
                "The provider returned an incomplete evaluation embedding batch."
            )
        results: list[CaseResult] = []
        for case in fixture.cases:
            results.append(
                await _evaluate_case(
                    case, fixture.evidence, document_vectors.vectors, embeddings, model
                )
            )
    finally:
        await client.aclose()
    return build_report(settings, model_metadata, results)


async def _evaluate_case(
    case: EvalCase,
    evidence: list[EvalEvidence],
    vectors: tuple[tuple[float, ...], ...],
    embeddings: NebiusEmbeddingProvider,
    model: NebiusGroundedModelProvider,
) -> CaseResult:
    query = await embeddings.embed_batch(
        [
            "Instruct: Retrieve engineering evidence that directly answers the question.\n"
            f"Query: {case.question}"
        ]
    )
    candidates = [
        RetrievalCandidate(item.id, item.text, vector)
        for item, vector in zip(evidence, vectors, strict=True)
    ]
    ranked = hybrid_rank(
        case.question,
        query.vectors[0],
        candidates,
        limit=4,
    )
    retrieved_ids = [item.evidence_id for item in ranked]
    relevant = set(case.relevant_evidence_ids)
    retrieval_hit = bool(relevant & set(retrieved_ids)) if case.answerable else False
    if not retrieved_ids:
        return CaseResult(
            id=case.id,
            answerable=case.answerable,
            retrieved_evidence_ids=[],
            retrieval_hit=False,
            grounded_success=False,
            negative_success=not case.answerable,
            emitted_claims=0,
            valid_verified_claims=0,
        )
    evidence_by_id = {item.id: item for item in evidence}
    excerpts = [EvidenceExcerpt(item_id, evidence_by_id[item_id].text) for item_id in retrieved_ids]
    try:
        generation = await model.generate(case.question, excerpts)
        verification = await model.verify(generation, excerpts)
    except DomainError as error:
        return CaseResult(
            id=case.id,
            answerable=case.answerable,
            retrieved_evidence_ids=retrieved_ids,
            retrieval_hit=retrieval_hit,
            grounded_success=False,
            negative_success=False,
            emitted_claims=0,
            valid_verified_claims=0,
            error_code=error.code,
        )
    outcomes = {item.claim_id: item for item in verification.outcomes}
    supported = [
        claim for claim in generation.claims if outcomes[claim.claim_id].verdict == "supported"
    ]
    valid = [
        claim
        for claim in supported
        if set(claim.evidence_ids) <= set(retrieved_ids)
        and (not case.answerable or bool(set(claim.evidence_ids) & relevant))
    ]
    return CaseResult(
        id=case.id,
        answerable=case.answerable,
        retrieved_evidence_ids=retrieved_ids,
        retrieval_hit=retrieval_hit,
        grounded_success=case.answerable and retrieval_hit and bool(valid),
        negative_success=not case.answerable and not supported,
        emitted_claims=len(supported),
        valid_verified_claims=len(valid),
    )


def build_report(
    settings: Settings,
    model_metadata: list[dict[str, object]],
    results: list[CaseResult],
) -> dict[str, object]:
    answerable = [item for item in results if item.answerable]
    negative = [item for item in results if not item.answerable]
    retrieval_hits = sum(item.retrieval_hit for item in answerable)
    grounded = sum(item.grounded_success for item in answerable)
    negative_successes = sum(item.negative_success for item in negative)
    emitted = sum(item.emitted_claims for item in results)
    valid = sum(item.valid_verified_claims for item in results)
    metrics = {
        "retrieval_recall_at_4": retrieval_hits / len(answerable),
        "grounded_answer_successes": grounded,
        "answerable_cases": len(answerable),
        "negative_successes": negative_successes,
        "negative_cases": len(negative),
        "valid_verified_claim_ratio": valid / emitted if emitted else 1.0,
    }
    passed = (
        metrics["retrieval_recall_at_4"] >= 0.9
        and grounded >= 10
        and negative_successes == len(negative)
        and metrics["valid_verified_claim_ratio"] == 1.0
    )
    return {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "provider": "nebius-token-factory",
        "generation_model": settings.nebius_generation_model,
        "generation_prompt_version": GENERATION_PROMPT_VERSION,
        "embedding_model": settings.nebius_embedding_model,
        "embedding_dimensions": settings.nebius_embedding_dimensions,
        "verification_prompt_version": VERIFICATION_PROMPT_VERSION,
        "model_metadata": model_metadata,
        "metrics": metrics,
        "passed": passed,
        "cases": [asdict(item) for item in results],
    }


def _required_model_metadata(
    payload: dict[str, object], required_ids: set[str]
) -> list[dict[str, object]]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ProviderInvalidResponseError("The provider model catalog was malformed.")
    records = [item for item in data if isinstance(item, dict) and item.get("id") in required_ids]
    found = {str(item["id"]) for item in records}
    missing = required_ids - found
    if missing:
        raise RuntimeError(
            f"Configured Nebius models are unavailable: {', '.join(sorted(missing))}"
        )
    allowed = {"id", "status", "context_length", "features", "regions"}
    return [{key: value for key, value in item.items() if key in allowed} for item in records]


def require_live_attestations(*, zdr_attested: bool, benchmark_permission_attested: bool) -> None:
    if not benchmark_permission_attested:
        raise RuntimeError(
            "Attest that written confirmation from Nebius or qualified counsel has been obtained for this thresholded live evaluation."
        )
    if not zdr_attested:
        raise RuntimeError(
            "Attest that organization-level Nebius ZDR is enabled before running live evaluation."
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Vikram's grounded-answer evaluation.")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("evals/grounded_answers/fixture_v1.json"),
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--attest-zdr",
        action="store_true",
        help="Attest that organization-level Nebius Zero Data Retention is enabled.",
    )
    parser.add_argument(
        "--attest-benchmark-permission",
        action="store_true",
        help=(
            "Attest that written confirmation from Nebius or qualified counsel has been "
            "obtained for this thresholded live evaluation."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=Path(".vikram/evals"))
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    fixture = load_fixture(args.fixture)
    validate_fixture_threshold_shape(fixture)
    if args.validate_only:
        print(f"Validated {len(fixture.cases)} synthetic grounded-answer cases.")
        return
    try:
        require_live_attestations(
            zdr_attested=args.attest_zdr,
            benchmark_permission_attested=args.attest_benchmark_permission,
        )
        settings = Settings(
            provider_mode="nebius", api_token="evaluation-only-capability-token-000000000000"
        )
        report = asyncio.run(
            run_live(
                fixture,
                settings,
                zdr_attested=args.attest_zdr,
                benchmark_permission_attested=args.attest_benchmark_permission,
            )
        )
    except (DomainError, RuntimeError) as error:
        print(f"Evaluation stopped: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"grounded-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote redacted evaluation report to {output}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
