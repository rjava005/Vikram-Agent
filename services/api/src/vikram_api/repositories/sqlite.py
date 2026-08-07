from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from vikram_api.domain.models import ConflictError, Evidence, NotFoundError


class SqliteRepository:
    def __init__(self, database_path: Path, migrations_dir: Path | None = None) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.migrations_dir = migrations_dir or Path(__file__).resolve().parents[3] / "migrations"
        self.migrate()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                row["version"]
                for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
            }
            for migration in sorted(self.migrations_dir.glob("*.sql")):
                if migration.stem in applied:
                    continue
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (migration.stem, datetime.now(UTC).isoformat()),
                )

    def create_project(self, project_id: str, name: str, created_at: str) -> dict[str, Any]:
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO projects(id, name, created_at) VALUES (?, ?, ?)",
                (project_id, name, created_at),
            )
        return {"id": project_id, "name": name, "created_at": created_at}

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, created_at FROM projects ORDER BY created_at, id"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_project(self, project_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id, name, created_at FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("Project not found.")
        return dict(row)

    def create_source(
        self,
        *,
        source_id: str,
        version_id: str,
        project_id: str,
        name: str,
        kind: str,
        sha256: str,
        storage_key: str,
        parser_id: str,
        evidence: list[tuple[str, int, str, str, str]],
        created_at: str,
    ) -> dict[str, Any]:
        with self.transaction() as connection:
            if (
                connection.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone()
                is None
            ):
                raise NotFoundError("Project not found.")
            connection.execute(
                "INSERT INTO sources(id, project_id, name, kind, status, created_at) VALUES (?, ?, ?, ?, 'ready', ?)",
                (source_id, project_id, name, kind, created_at),
            )
            connection.execute(
                "INSERT INTO source_versions(id, source_id, sha256, storage_key, parser_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (version_id, source_id, sha256, storage_key, parser_id, created_at),
            )
            connection.executemany(
                "INSERT INTO evidence_units(id, source_version_id, ordinal, content, locator_kind, locator_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(row[0], version_id, *row[1:], created_at) for row in evidence],
            )
        return {
            "id": source_id,
            "project_id": project_id,
            "version_id": version_id,
            "name": name,
            "kind": kind,
            "status": "ready",
            "evidence_count": len(evidence),
            "created_at": created_at,
        }

    def list_sources(self, project_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT s.id, s.project_id, sv.id AS version_id, s.name, s.kind, s.status,
                       COUNT(e.id) AS evidence_count, s.created_at
                FROM sources s
                JOIN source_versions sv ON sv.source_id = s.id
                LEFT JOIN evidence_units e ON e.source_version_id = sv.id
                WHERE s.project_id = ?
                GROUP BY s.id, sv.id
                ORDER BY s.created_at, s.id
                """,
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_evidence(self, project_id: str) -> list[Evidence]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT e.id, s.id AS source_id, sv.id AS source_version_id, s.name AS source_name,
                       e.content, e.locator_kind, e.locator_json
                FROM evidence_units e
                JOIN source_versions sv ON sv.id = e.source_version_id
                JOIN sources s ON s.id = sv.source_id
                WHERE s.project_id = ? AND s.status = 'ready'
                ORDER BY s.created_at, e.ordinal
                """,
                (project_id,),
            ).fetchall()
        return [
            Evidence(
                id=row["id"],
                source_id=row["source_id"],
                source_version_id=row["source_version_id"],
                source_name=row["source_name"],
                content=row["content"],
                locator_kind=cast(Literal["pdf_page", "markdown_section"], row["locator_kind"]),
                locator=json.loads(row["locator_json"]),
            )
            for row in rows
        ]

    def create_answer(self, *, answer: dict[str, Any], citations: list[dict[str, Any]]) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO answers(id, project_id, question, answer_text, grounding, provider_id, prompt_version, created_at)
                VALUES (:id, :project_id, :question, :text, :grounding, :provider_id, :prompt_version, :created_at)
                """,
                answer,
            )
            connection.executemany(
                """
                INSERT INTO answer_citations(id, answer_id, evidence_id, ordinal, excerpt, claim_id)
                VALUES (:id, :answer_id, :evidence_id, :ordinal, :excerpt, :claim_id)
                """,
                citations,
            )

    def get_answer_record(self, answer_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM answers WHERE id = ?", (answer_id,)).fetchone()
        if row is None:
            raise NotFoundError("Answer not found.")
        return dict(row)

    def upsert_feedback(
        self, *, observation_id: str, answer_id: str, status: str, now: str
    ) -> dict[str, Any]:
        with self.transaction() as connection:
            if (
                connection.execute("SELECT 1 FROM answers WHERE id = ?", (answer_id,)).fetchone()
                is None
            ):
                raise NotFoundError("Answer not found.")
            existing = connection.execute(
                "SELECT id, created_at FROM learning_observations WHERE answer_id = ?", (answer_id,)
            ).fetchone()
            if existing:
                connection.execute(
                    "UPDATE learning_observations SET status = ?, updated_at = ? WHERE answer_id = ?",
                    (status, now, answer_id),
                )
                observation_id, created_at = existing["id"], existing["created_at"]
            else:
                connection.execute(
                    "INSERT INTO learning_observations(id, answer_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (observation_id, answer_id, status, now, now),
                )
                created_at = now
        return {
            "id": observation_id,
            "answer_id": answer_id,
            "status": status,
            "created_at": created_at,
            "updated_at": now,
        }

    def create_task_from_answer(
        self, *, task_id: str, answer_id: str, title: str, created_at: str
    ) -> dict[str, Any]:
        answer = self.get_answer_record(answer_id)
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO tasks(id, project_id, source_answer_id, title, status, created_at) VALUES (?, ?, ?, ?, 'todo', ?)",
                (task_id, answer["project_id"], answer_id, title, created_at),
            )
        return {
            "id": task_id,
            "project_id": answer["project_id"],
            "source_answer_id": answer_id,
            "title": title,
            "status": "todo",
            "created_at": created_at,
            "completed_at": None,
        }

    def list_tasks(self, project_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY status, created_at, id",
                (project_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_focus(
        self, *, focus_id: str, task_id: str, duration_seconds: int, now: str
    ) -> dict[str, Any]:
        with self.transaction() as connection:
            if (
                connection.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone()
                is None
            ):
                raise NotFoundError("Task not found.")
            connection.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
            connection.execute(
                """
                INSERT INTO focus_sessions(id, task_id, status, duration_seconds, elapsed_active_seconds,
                    current_segment_started_at, revision, created_at)
                VALUES (?, ?, 'active', ?, 0, ?, 0, ?)
                """,
                (focus_id, task_id, duration_seconds, now, now),
            )
            connection.execute(
                "INSERT INTO focus_events(id, focus_session_id, event_type, revision, occurred_at) VALUES (?, ?, 'start', 0, ?)",
                (f"{focus_id}:0", focus_id, now),
            )
        return self.get_focus(focus_id)

    def get_focus(self, focus_id: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM focus_sessions WHERE id = ?", (focus_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError("Focus session not found.")
        return dict(row)

    def get_active_focus_for_project(self, project_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT f.* FROM focus_sessions f JOIN tasks t ON t.id = f.task_id
                WHERE t.project_id = ? AND f.status IN ('active', 'paused')
                ORDER BY f.created_at DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        return dict(row) if row else None

    def transition_focus(
        self,
        *,
        focus_id: str,
        expected_revision: int,
        status: str,
        elapsed_seconds: int,
        segment_started_at: str | None,
        completed_at: str | None,
        transition: str,
        now: str,
    ) -> dict[str, Any]:
        new_revision = expected_revision + 1
        with self.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE focus_sessions SET status = ?, elapsed_active_seconds = ?,
                    current_segment_started_at = ?, completed_at = ?, revision = ?
                WHERE id = ? AND revision = ?
                """,
                (
                    status,
                    elapsed_seconds,
                    segment_started_at,
                    completed_at,
                    new_revision,
                    focus_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise ConflictError("Focus session changed; refresh before retrying.")
            connection.execute(
                "INSERT INTO focus_events(id, focus_session_id, event_type, revision, occurred_at) VALUES (?, ?, ?, ?, ?)",
                (f"{focus_id}:{new_revision}", focus_id, transition, new_revision, now),
            )
            if status == "completed":
                task_id = connection.execute(
                    "SELECT task_id FROM focus_sessions WHERE id = ?", (focus_id,)
                ).fetchone()["task_id"]
                connection.execute(
                    "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
                    (now, task_id),
                )
        return self.get_focus(focus_id)
