from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from vikram_api.app_factory import API_TOKEN_HEADER, create_app
from vikram_api.config import Settings

TOKEN = "remote-test-capability-token-0000000000000000000"


class NebiusMock:
    def __init__(self, *, verdict: str = "supported") -> None:
        self.verdict = verdict
        self.requests: list[tuple[str, dict[str, object]]] = []

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        self.requests.append((request.url.path, payload))
        if request.url.path.endswith("/embeddings"):
            inputs = payload["input"]
            assert isinstance(inputs, list)
            vectors = []
            for index, text in enumerate(inputs):
                assert isinstance(text, str)
                vector = [0.0] * 32
                vector[0 if "phase" in text.lower() else 1] = 1.0
                vectors.append({"index": index, "embedding": vector})
            return httpx.Response(
                200,
                json={"data": vectors, "usage": {"prompt_tokens": len(inputs)}},
            )

        schema_name = payload["response_format"]["json_schema"]["name"]
        messages = payload["messages"]
        user_prompt = messages[1]["content"]
        if schema_name == "vikram_grounded_answer":
            evidence_ids = re.findall(r'"evidence_id":"([^"]+)"', user_prompt)
            assert evidence_ids
            content = {
                "answer": "This top-level draft must not be displayed before verification.",
                "claims": [
                    {
                        "claim_id": "claim-remote-1",
                        "text": "Phase margin measures distance from feedback-loop instability.",
                        "evidence_ids": [evidence_ids[0]],
                    }
                ],
            }
        else:
            content = {
                "outcomes": [
                    {
                        "claim_id": "claim-remote-1",
                        "verdict": self.verdict,
                        "reason": "The cited evidence directly supports the claim.",
                    }
                ]
            }
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(content)}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            },
        )


def configured_client(tmp_path: Path, handler: Callable[[httpx.Request], object]) -> TestClient:
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            provider_mode="nebius",
            api_token=TOKEN,
            nebius_api_key="test-key-never-logged",
            nebius_embedding_dimensions=32,
        ),
        remote_transport=httpx.MockTransport(handler),
    )
    client = TestClient(app)
    client.headers[API_TOKEN_HEADER] = TOKEN
    return client


def create_remote_project(client: TestClient) -> dict[str, object]:
    project = client.post("/api/v1/projects", json={"name": "Remote grounding"}).json()
    imported = client.post(
        f"/api/v1/projects/{project['id']}/sources",
        files={
            "file": (
                "control.md",
                b"# Stability\nPhase margin measures distance from feedback-loop instability.",
                "text/markdown",
            )
        },
    )
    assert imported.status_code == 201
    return project


def test_remote_answer_requires_policy_then_caches_embeddings(tmp_path: Path) -> None:
    provider = NebiusMock()
    with configured_client(tmp_path, provider) as client:
        project = create_remote_project(client)

        local_answer = client.post(
            f"/api/v1/projects/{project['id']}/answers",
            json={"question": "What does phase margin measure?"},
        )
        assert local_answer.status_code == 201
        assert local_answer.json()["provenance"]["provider_mode"] == "fake"
        assert provider.requests == []

        enabled = client.put(
            f"/api/v1/projects/{project['id']}/ai-policy",
            json={"mode": "nebius", "zdr_attested": True, "expected_revision": 0},
        )
        assert enabled.status_code == 200

        first = client.post(
            f"/api/v1/projects/{project['id']}/answers",
            json={"question": "What does phase margin measure?"},
        )
        assert first.status_code == 201, first.text
        answer = first.json()
        assert answer["text"] == ("Phase margin measures distance from feedback-loop instability.")
        assert answer["provenance"]["verification"] == "remote_verified"
        assert answer["citations"][0]["locator"]["heading"] == "Stability"

        document_embedding_calls = [
            payload
            for path, payload in provider.requests
            if path.endswith("/embeddings") and not str(payload["input"][0]).startswith("Instruct:")
        ]
        assert len(document_embedding_calls) == 1

        second = client.post(
            f"/api/v1/projects/{project['id']}/answers",
            json={"question": "How is phase margin defined?"},
        )
        assert second.status_code == 201, second.text
        document_embedding_calls = [
            payload
            for path, payload in provider.requests
            if path.endswith("/embeddings") and not str(payload["input"][0]).startswith("Instruct:")
        ]
        assert len(document_embedding_calls) == 1


def test_wrong_dimension_cached_embedding_is_ignored_and_reembedded(tmp_path: Path) -> None:
    provider = NebiusMock()
    with configured_client(tmp_path, provider) as client:
        project = create_remote_project(client)
        enabled = client.put(
            f"/api/v1/projects/{project['id']}/ai-policy",
            json={"mode": "nebius", "zdr_attested": True, "expected_revision": 0},
        )
        assert enabled.status_code == 200
        repository = client.app.state.vikram_service.repository
        evidence = repository.list_evidence(str(project["id"]))[0]
        content_hash = hashlib.sha256(evidence.content.encode("utf-8")).hexdigest()
        repository.store_embeddings(
            project_id=str(project["id"]),
            provider_id="nebius-token-factory",
            model_id="Qwen/Qwen3-Embedding-8B",
            records=[(evidence.id, content_hash, (1.0, 0.0, 0.0))],
            expected_policy_revision=1,
            created_at="2026-08-14T00:00:00Z",
        )

        answer = client.post(
            f"/api/v1/projects/{project['id']}/answers",
            json={"question": "What does phase margin measure?"},
        )
        assert answer.status_code == 201, answer.text
        document_embedding_calls = [
            payload
            for path, payload in provider.requests
            if path.endswith("/embeddings") and not str(payload["input"][0]).startswith("Instruct:")
        ]
        assert len(document_embedding_calls) == 1
        cached = repository.get_cached_embeddings(
            project_id=str(project["id"]),
            provider_id="nebius-token-factory",
            model_id="Qwen/Qwen3-Embedding-8B",
            expected_dimensions=32,
            content_hashes={evidence.id: content_hash},
        )
        assert len(cached[evidence.id]) == 32


def test_oversized_evidence_fails_before_any_provider_call(tmp_path: Path) -> None:
    provider = NebiusMock()
    app = create_app(
        Settings(
            data_dir=tmp_path / "data",
            provider_mode="nebius",
            api_token=TOKEN,
            nebius_api_key="test-key-never-logged",
            nebius_embedding_dimensions=32,
            nebius_max_evidence_characters=1_000,
        ),
        remote_transport=httpx.MockTransport(provider),
    )
    with TestClient(app, headers={API_TOKEN_HEADER: TOKEN}) as client:
        project = client.post("/api/v1/projects", json={"name": "Oversized"}).json()
        imported = client.post(
            f"/api/v1/projects/{project['id']}/sources",
            files={
                "file": (
                    "oversized.md",
                    ("# Large section\n" + ("x" * 1_001)).encode(),
                    "text/markdown",
                )
            },
        )
        assert imported.status_code == 201
        enabled = client.put(
            f"/api/v1/projects/{project['id']}/ai-policy",
            json={"mode": "nebius", "zdr_attested": True, "expected_revision": 0},
        )
        assert enabled.status_code == 200

        rejected = client.post(
            f"/api/v1/projects/{project['id']}/answers",
            json={"question": "What is in the section?"},
        )
        assert rejected.status_code == 422
        assert rejected.json()["code"] == "remote_index_limit"
        assert provider.requests == []


def test_revocation_during_embedding_cancels_run_without_cache_or_answer(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        embedding_started = asyncio.Event()
        embedding_cancelled = asyncio.Event()
        release_embedding = asyncio.Event()
        provider_requests: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            provider_requests.append(request.url.path)
            embedding_started.set()
            try:
                await release_embedding.wait()
            except asyncio.CancelledError:
                embedding_cancelled.set()
                raise
            raise AssertionError("revocation did not cancel the provider request")

        app = create_app(
            Settings(
                data_dir=tmp_path / "data",
                provider_mode="nebius",
                api_token=TOKEN,
                nebius_api_key="test-key-never-logged",
                nebius_embedding_dimensions=32,
            ),
            remote_transport=httpx.MockTransport(handler),
        )
        transport = httpx.ASGITransport(app=app)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={API_TOKEN_HEADER: TOKEN},
            ) as client,
        ):
            project = (await client.post("/api/v1/projects", json={"name": "Revoke"})).json()
            imported = await client.post(
                f"/api/v1/projects/{project['id']}/sources",
                files={
                    "file": (
                        "control.md",
                        b"# Stability\nPhase margin measures stability.",
                        "text/markdown",
                    )
                },
            )
            assert imported.status_code == 201
            enabled = await client.put(
                f"/api/v1/projects/{project['id']}/ai-policy",
                json={"mode": "nebius", "zdr_attested": True, "expected_revision": 0},
            )
            assert enabled.status_code == 200
            answer_task = asyncio.create_task(
                client.post(
                    f"/api/v1/projects/{project['id']}/answers",
                    json={"question": "What does phase margin measure?"},
                )
            )
            await asyncio.wait_for(embedding_started.wait(), timeout=2)
            try:
                revoked = await asyncio.wait_for(
                    client.put(
                        f"/api/v1/projects/{project['id']}/ai-policy",
                        json={
                            "mode": "local",
                            "zdr_attested": False,
                            "expected_revision": 1,
                        },
                    ),
                    timeout=2,
                )
            finally:
                release_embedding.set()
            assert revoked.status_code == 200
            assert revoked.json()["mode"] == "local"
            canceled_answer = await answer_task
            assert canceled_answer.status_code == 409
            assert canceled_answer.json()["code"] == "conflict"
            await asyncio.wait_for(embedding_cancelled.wait(), timeout=2)
            assert provider_requests == ["/v1/embeddings"]
            repository = app.state.vikram_service.repository
            with repository.connect() as connection:
                embedding_count = connection.execute(
                    "SELECT COUNT(*) FROM evidence_embeddings"
                ).fetchone()[0]
                answer_count = connection.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
            assert embedding_count == 0
            assert answer_count == 0

    asyncio.run(scenario())


def test_failed_remote_verification_does_not_persist_answer(tmp_path: Path) -> None:
    provider = NebiusMock(verdict="unsupported")
    with configured_client(tmp_path, provider) as client:
        project = create_remote_project(client)
        enabled = client.put(
            f"/api/v1/projects/{project['id']}/ai-policy",
            json={"mode": "nebius", "zdr_attested": True, "expected_revision": 0},
        )
        assert enabled.status_code == 200

        rejected = client.post(
            f"/api/v1/projects/{project['id']}/answers",
            json={"question": "What does phase margin measure?"},
        )
        assert rejected.status_code == 422
        assert rejected.json()["code"] == "grounding_verification"
        repository = client.app.state.vikram_service.repository
        with repository.connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
        assert count == 0


def test_cancelled_remote_request_cancels_provider_and_does_not_persist(tmp_path: Path) -> None:
    provider_started = asyncio.Event()
    provider_cancelled = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/embeddings"):
            payload = json.loads(request.content)
            inputs = payload["input"]
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"index": index, "embedding": [1.0] + ([0.0] * 31)}
                        for index in range(len(inputs))
                    ]
                },
            )
        provider_started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            provider_cancelled.set()
            raise
        raise AssertionError("unreachable")

    async def scenario() -> None:
        app = create_app(
            Settings(
                data_dir=tmp_path / "data",
                provider_mode="nebius",
                api_token=TOKEN,
                nebius_api_key="test-key-never-logged",
                nebius_embedding_dimensions=32,
            ),
            remote_transport=httpx.MockTransport(handler),
        )
        transport = httpx.ASGITransport(app=app)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={API_TOKEN_HEADER: TOKEN},
            ) as client,
        ):
            project = (await client.post("/api/v1/projects", json={"name": "Cancel"})).json()
            imported = await client.post(
                f"/api/v1/projects/{project['id']}/sources",
                files={
                    "file": (
                        "control.md",
                        b"# Stability\nPhase margin measures stability.",
                        "text/markdown",
                    )
                },
            )
            assert imported.status_code == 201
            enabled = await client.put(
                f"/api/v1/projects/{project['id']}/ai-policy",
                json={"mode": "nebius", "zdr_attested": True, "expected_revision": 0},
            )
            assert enabled.status_code == 200
            request_task = asyncio.create_task(
                client.post(
                    f"/api/v1/projects/{project['id']}/answers",
                    json={"question": "What does phase margin measure?"},
                )
            )
            await asyncio.wait_for(provider_started.wait(), timeout=2)
            request_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request_task
            await asyncio.wait_for(provider_cancelled.wait(), timeout=2)
            repository = app.state.vikram_service.repository
            with repository.connect() as connection:
                count = connection.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
            assert count == 0

    asyncio.run(scenario())
