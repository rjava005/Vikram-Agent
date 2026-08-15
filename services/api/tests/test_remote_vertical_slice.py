from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

import httpx
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
