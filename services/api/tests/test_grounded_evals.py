from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from vikram_api.config import Settings
from vikram_api.domain.models import ProviderTimeoutError
from vikram_api.evals.grounded import (
    CaseResult,
    EvalCase,
    EvalEvidence,
    _evaluate_case,
    build_report,
    load_fixture,
    main,
    parse_args,
    run_live,
    validate_fixture_threshold_shape,
)
from vikram_api.providers.nebius import GENERATION_PROMPT_VERSION, VERIFICATION_PROMPT_VERSION


def fixture_path() -> Path:
    return Path(__file__).resolve().parents[3] / "evals" / "grounded_answers" / "fixture_v1.json"


def test_synthetic_fixture_has_required_answerable_and_negative_cases() -> None:
    fixture = load_fixture(fixture_path())
    validate_fixture_threshold_shape(fixture)
    assert sum(case.answerable for case in fixture.cases) == 12
    assert sum(not case.answerable for case in fixture.cases) == 4


def test_report_thresholds_are_explicit_and_redacted() -> None:
    results = [
        CaseResult(
            id=f"answerable-{index}",
            answerable=True,
            retrieved_evidence_ids=[f"evidence-{index}"],
            retrieval_hit=index < 11,
            grounded_success=index < 10,
            negative_success=False,
            emitted_claims=1,
            valid_verified_claims=1,
        )
        for index in range(12)
    ] + [
        CaseResult(
            id=f"negative-{index}",
            answerable=False,
            retrieved_evidence_ids=[],
            retrieval_hit=False,
            grounded_success=False,
            negative_success=True,
            emitted_claims=0,
            valid_verified_claims=0,
        )
        for index in range(4)
    ]
    report = build_report(
        Settings(),
        [{"id": "model", "status": "active"}],
        results,
    )
    assert report["passed"] is True
    assert report["metrics"]["retrieval_recall_at_4"] == 11 / 12
    assert report["generation_prompt_version"] == GENERATION_PROMPT_VERSION
    assert report["verification_prompt_version"] == VERIFICATION_PROMPT_VERSION
    assert "question" not in str(report)
    assert "text" not in str(report)


def test_provider_timeout_does_not_count_as_negative_success() -> None:
    class Embeddings:
        async def embed_batch(self, _texts: list[str]) -> object:
            return SimpleNamespace(vectors=((1.0, 0.0),))

    class TimeoutModel:
        async def generate(self, _question: str, _evidence: object) -> object:
            raise ProviderTimeoutError("Provider timed out during a negative case.")

    result = asyncio.run(
        _evaluate_case(
            EvalCase(
                id="negative-timeout",
                question="What does phase margin mean?",
                answerable=False,
                relevant_evidence_ids=[],
            ),
            [EvalEvidence(id="evidence-1", text="Phase margin measures stability distance.")],
            ((1.0, 0.0),),
            Embeddings(),  # type: ignore[arg-type]
            TimeoutModel(),  # type: ignore[arg-type]
        )
    )
    assert result.error_code == "provider_timeout"
    assert result.negative_success is False


def test_live_eval_requires_explicit_benchmark_permission_before_key_or_model_calls() -> None:
    fixture = load_fixture(fixture_path())
    with pytest.raises(RuntimeError, match="written confirmation from Nebius or qualified counsel"):
        asyncio.run(
            run_live(
                fixture,
                Settings(nebius_api_key=""),
                zdr_attested=True,
                benchmark_permission_attested=False,
            )
        )
    args = parse_args(["--attest-benchmark-permission"])
    assert args.attest_benchmark_permission is True


def test_validate_only_remains_offline(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["grounded-eval", "--fixture", str(fixture_path()), "--validate-only"],
    )
    main()
    assert "Validated 16 synthetic grounded-answer cases." in capsys.readouterr().out
