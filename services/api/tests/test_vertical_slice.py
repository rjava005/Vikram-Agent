from __future__ import annotations

from fastapi.testclient import TestClient


def test_complete_markdown_vertical_slice(api_client: TestClient) -> None:
    health = api_client.get("/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "api_version": "v1",
        "provider_mode": "fake",
        "persistence": "sqlite",
    }

    created = api_client.post("/api/v1/projects", json={"name": "Motor controller"})
    assert created.status_code == 201
    project = created.json()

    imported = api_client.post(
        f"/api/v1/projects/{project['id']}/sources",
        files={
            "file": (
                "control.md",
                b"# Stability\nPhase margin measures how far a feedback loop is from instability.\n",
                "text/markdown",
            )
        },
    )
    assert imported.status_code == 201, imported.text
    source = imported.json()
    assert source["evidence_count"] == 1

    answered = api_client.post(
        f"/api/v1/projects/{project['id']}/answers",
        json={"question": "What does phase margin measure?"},
    )
    assert answered.status_code == 201, answered.text
    answer = answered.json()
    assert answer["grounding"] == "grounded"
    assert answer["citations"][0]["source_id"] == source["id"]
    assert answer["citations"][0]["locator"] == {
        "kind": "markdown_section",
        "heading": "Stability",
        "line_start": 1,
        "line_end": 2,
    }

    for feedback_status in ("understood", "unclear", "review_later"):
        feedback = api_client.put(
            f"/api/v1/answers/{answer['id']}/feedback", json={"status": feedback_status}
        )
        assert feedback.status_code == 200
        assert feedback.json()["status"] == feedback_status

    task_response = api_client.post(
        f"/api/v1/answers/{answer['id']}/tasks", json={"title": "Review loop stability"}
    )
    assert task_response.status_code == 201
    task = task_response.json()

    focus_response = api_client.post(
        f"/api/v1/tasks/{task['id']}/focus-sessions", json={"duration_minutes": 1}
    )
    assert focus_response.status_code == 201
    focus = focus_response.json()
    assert focus["status"] == "active"

    for transition, expected_status in (
        ("pause", "paused"),
        ("resume", "active"),
        ("complete", "completed"),
    ):
        response = api_client.post(
            f"/api/v1/focus-sessions/{focus['id']}/transitions",
            json={"transition": transition, "expected_revision": focus["revision"]},
        )
        assert response.status_code == 200, response.text
        focus = response.json()
        assert focus["status"] == expected_status

    workspace = api_client.get(f"/api/v1/projects/{project['id']}")
    assert workspace.status_code == 200
    assert workspace.json()["tasks"][0]["status"] == "completed"
    assert workspace.json()["active_focus"] is None


def test_rejects_unsupported_import_and_stale_focus_revision(api_client: TestClient) -> None:
    project = api_client.post("/api/v1/projects", json={"name": "Safety"}).json()
    rejected = api_client.post(
        f"/api/v1/projects/{project['id']}/sources",
        files={"file": ("notes.txt", b"private", "text/plain")},
    )
    assert rejected.status_code == 415
    assert rejected.headers["content-type"].startswith("application/problem+json")

    source = api_client.post(
        f"/api/v1/projects/{project['id']}/sources",
        files={"file": ("notes.md", b"# Evidence\nA fuse limits fault energy.", "text/markdown")},
    )
    assert source.status_code == 201
    answer = api_client.post(
        f"/api/v1/projects/{project['id']}/answers", json={"question": "What limits fault energy?"}
    ).json()
    task = api_client.post(f"/api/v1/answers/{answer['id']}/tasks", json={}).json()
    focus = api_client.post(
        f"/api/v1/tasks/{task['id']}/focus-sessions", json={"duration_minutes": 25}
    ).json()
    stale = api_client.post(
        f"/api/v1/focus-sessions/{focus['id']}/transitions",
        json={"transition": "pause", "expected_revision": 99},
    )
    assert stale.status_code == 409
