"""Tests for the Phase-8 write API (AS-031): POST /api/tasks + WS /ws/tasks/{id}.

Runs use the deterministic ``mock`` backend, so these exercise the real orchestrator end to end
(submit → background run → persisted result → live event stream) with no network or model. The
module skips cleanly when the ``[dashboard]`` extra is absent.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="dashboard extra not installed")
pytest.importorskip("httpx", reason="fastapi TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from immortals.dashboard.app import create_app  # noqa: E402

_PLAN = json.loads((Path(__file__).resolve().parents[1] / "scripts" / "sample_eigen_plan.json")
                   .read_text(encoding="utf-8"))
TASK = _PLAN["task_id"]


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "run.db")))


def _wait_terminal(client, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/api/tasks/{TASK}/status").json()["status"]
        if status in {"completed", "failed", "blocked"}:
            return status
        time.sleep(0.05)
    raise AssertionError("run did not reach a terminal state in time")


def test_post_starts_and_run_completes(client):
    resp = client.post("/api/tasks", json={"plan": _PLAN, "backend": "mock"})
    assert resp.status_code == 200
    assert resp.json() == {"task_id": TASK, "status": "started"}

    assert _wait_terminal(client) == "completed"

    # The run persisted to the same store the read API serves.
    detail = client.get(f"/api/runs/{TASK}").json()
    assert detail["status"] == "completed"
    assert set(detail["artifacts"]) == {"eigenvectors-lesson", "eigenvectors-quiz"}


def test_missing_plan_is_422(client):
    assert client.post("/api/tasks", json={}).status_code == 422


def test_invalid_plan_is_422(client):
    # Well-formed JSON but not a valid plan/v1 (no task_id/goal/nodes).
    assert client.post("/api/tasks", json={"plan": {"schema": "plan/v1"}}).status_code == 422


def test_status_unknown_before_start(client):
    assert client.get("/api/tasks/never-ran/status").json()["status"] == "unknown"


def test_websocket_streams_backlog_and_end(client):
    # Start and let it finish, then connect: the WS replays the full backlog + a terminal marker.
    client.post("/api/tasks", json={"plan": _PLAN, "backend": "mock"})
    _wait_terminal(client)

    types: list[str] = []
    with client.websocket_connect(f"/ws/tasks/{TASK}") as ws:
        while True:
            msg = ws.receive_json()
            types.append(msg.get("type"))
            if msg.get("type") == "__end__":
                assert msg["status"] == "completed"
                break
    assert "plan_validated" in types
    assert "run_completed" in types


def test_websocket_live_stream(client):
    # Connect BEFORE posting: subscriber is registered first, so live events stream through.
    with client.websocket_connect(f"/ws/tasks/{TASK}") as ws:
        client.post("/api/tasks", json={"plan": _PLAN, "backend": "mock"})
        seen: list[str] = []
        while True:
            msg = ws.receive_json()
            seen.append(msg.get("type"))
            if msg.get("type") == "__end__":
                break
    assert "run_completed" in seen
