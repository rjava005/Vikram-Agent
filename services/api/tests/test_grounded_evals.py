from __future__ import annotations

from pathlib import Path

from vikram_api.config import Settings
from vikram_api.evals.grounded import (
    CaseResult,
    build_report,
    load_fixture,
    validate_fixture_threshold_shape,
)


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
    assert "question" not in str(report)
    assert "text" not in str(report)
