from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

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
    repository.store_embeddings(
        project_id="project",
        provider_id="nebius",
        model_id="embedding-model",
        records=[("evidence", "content-hash", (0.125, -0.5, 1.0))],
        created_at="2026-08-07T00:00:00Z",
    )

    cached = repository.get_cached_embeddings(
        project_id="project",
        provider_id="nebius",
        model_id="embedding-model",
        content_hashes={"evidence": "content-hash"},
    )
    assert cached["evidence"] == pytest.approx((0.125, -0.5, 1.0))
    assert (
        repository.get_cached_embeddings(
            project_id="project",
            provider_id="nebius",
            model_id="embedding-model",
            content_hashes={"evidence": "changed"},
        )
        == {}
    )

    repository.update_ai_policy(
        project_id="project",
        mode="local",
        zdr_attested=False,
        expected_revision=0,
        updated_at="2026-08-07T00:01:00Z",
    )
    assert (
        repository.get_cached_embeddings(
            project_id="project",
            provider_id="nebius",
            model_id="embedding-model",
            content_hashes={"evidence": "content-hash"},
        )
        == {}
    )
