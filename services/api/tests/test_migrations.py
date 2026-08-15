from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vikram_api.domain.models import ConflictError
from vikram_api.repositories.sqlite import SqliteRepository


def test_migrates_existing_mvp_database_to_local_ai_policy(tmp_path: Path) -> None:
    database_path = tmp_path / "vikram.sqlite3"
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    connection = sqlite3.connect(database_path)
    connection.executescript((migrations_dir / "0001_mvp.sql").read_text(encoding="utf-8"))
    connection.execute(
        "CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    connection.execute(
        "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
        ("0001_mvp", datetime.now(UTC).isoformat()),
    )
    connection.execute(
        "INSERT INTO projects(id, name, created_at) VALUES (?, ?, ?)",
        ("project-before-0002", "Existing project", "2026-08-07T00:00:00Z"),
    )
    connection.commit()
    connection.close()

    repository = SqliteRepository(database_path, migrations_dir=migrations_dir)

    assert repository.get_project("project-before-0002")["name"] == "Existing project"
    assert repository.get_ai_policy("project-before-0002") == {
        "project_id": "project-before-0002",
        "mode": "local",
        "zdr_attested": False,
        "revision": 0,
        "updated_at": "2026-08-07T00:00:00Z",
    }
    with repository.connect() as migrated:
        versions = {
            row["version"]
            for row in migrated.execute("SELECT version FROM schema_migrations").fetchall()
        }
    assert versions == {"0001_mvp", "0002_real_ai_quality"}


def test_embedding_cache_uses_content_hash_and_is_removed_on_revocation(tmp_path: Path) -> None:
    repository = SqliteRepository(tmp_path / "vikram.sqlite3")
    repository.create_project("project", "Cache", "2026-08-07T00:00:00Z")
    repository.create_source(
        source_id="source",
        version_id="version",
        project_id="project",
        name="notes.md",
        kind="markdown",
        sha256="source-hash",
        storage_key="sha256/source-hash",
        parser_id="test",
        evidence=[
            (
                "evidence",
                0,
                "A grounded fact.",
                "markdown_section",
                '{"kind":"markdown_section","heading":"Fact","line_start":1,"line_end":2}',
            )
        ],
        created_at="2026-08-07T00:00:00Z",
    )
    repository.update_ai_policy(
        project_id="project",
        mode="nebius",
        zdr_attested=True,
        expected_revision=0,
        updated_at="2026-08-07T00:00:30Z",
    )
    repository.store_embeddings(
        project_id="project",
        provider_id="nebius",
        model_id="embedding-model",
        records=[("evidence", "content-hash", (0.125, -0.5, 1.0))],
        expected_policy_revision=1,
        created_at="2026-08-07T00:00:00Z",
    )

    cached = repository.get_cached_embeddings(
        project_id="project",
        provider_id="nebius",
        model_id="embedding-model",
        expected_dimensions=3,
        content_hashes={"evidence": "content-hash"},
    )
    assert cached["evidence"] == pytest.approx((0.125, -0.5, 1.0))
    assert (
        repository.get_cached_embeddings(
            project_id="project",
            provider_id="nebius",
            model_id="embedding-model",
            expected_dimensions=3,
            content_hashes={"evidence": "changed"},
        )
        == {}
    )
    repository.update_ai_policy(
        project_id="project",
        mode="local",
        zdr_attested=False,
        expected_revision=1,
        updated_at="2026-08-07T00:01:00Z",
    )
    assert (
        repository.get_cached_embeddings(
            project_id="project",
            provider_id="nebius",
            model_id="embedding-model",
            expected_dimensions=3,
            content_hashes={"evidence": "content-hash"},
        )
        == {}
    )
    with pytest.raises(ConflictError, match="in-flight run was canceled"):
        repository.store_embeddings(
            project_id="project",
            provider_id="nebius",
            model_id="embedding-model",
            records=[("evidence", "content-hash", (0.25, 0.5, 0.75))],
            expected_policy_revision=1,
            created_at="2026-08-07T00:02:00Z",
        )


def test_stale_remote_policy_revision_blocks_final_answer_persistence(tmp_path: Path) -> None:
    repository = SqliteRepository(tmp_path / "vikram.sqlite3")
    repository.create_project("project", "Answer guard", "2026-08-07T00:00:00Z")
    repository.update_ai_policy(
        project_id="project",
        mode="nebius",
        zdr_attested=True,
        expected_revision=0,
        updated_at="2026-08-07T00:01:00Z",
    )
    repository.update_ai_policy(
        project_id="project",
        mode="local",
        zdr_attested=False,
        expected_revision=1,
        updated_at="2026-08-07T00:02:00Z",
    )

    with pytest.raises(ConflictError, match="in-flight run was canceled"):
        repository.create_answer(
            answer={
                "id": "answer",
                "project_id": "project",
                "question": "What changed?",
                "text": "A stale remote answer.",
                "grounding": "grounded",
                "provider_id": "nebius-token-factory",
                "prompt_version": "test-v1",
                "created_at": "2026-08-07T00:03:00Z",
            },
            citations=[],
            answer_run={
                "answer_id": "answer",
                "provider_mode": "nebius",
                "model_id": "generation-model",
                "embedding_model_id": "embedding-model",
                "retrieval_strategy": "hybrid",
                "verifier_model_id": "verification-model",
                "verifier_prompt_version": "verify-v1",
                "candidate_count": 0,
                "selected_evidence_count": 0,
                "generation_latency_ms": 1,
                "verification_latency_ms": 1,
                "input_tokens": 1,
                "output_tokens": 1,
                "created_at": "2026-08-07T00:03:00Z",
            },
            retrieval_candidates=[],
            claim_verifications=[],
            expected_ai_policy_revision=1,
        )
    with repository.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM answers").fetchone()[0] == 0
