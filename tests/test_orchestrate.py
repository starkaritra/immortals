"""Tests for goal→plan planning + the orchestrate endpoint (AS-033).

`plan_via_route` needs no key (registry routing); the orchestrate endpoint is driven end to end
with `planner=route` + the `mock` worker backend, so a real multi-node DAG runs deterministically
with no network. `plan_via_manager` is exercised with a FakeProvider that returns plan JSON.
"""

from __future__ import annotations

import time

import pytest

pytest.importorskip("fastapi", reason="dashboard extra not installed")
pytest.importorskip("httpx", reason="fastapi TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from immortals.contracts.models import Plan  # noqa: E402
from immortals.dashboard.app import create_app  # noqa: E402
from immortals.dashboard.planner import plan_via_manager, plan_via_route  # noqa: E402
from immortals.runners.providers import FakeProvider, ProviderResponse  # noqa: E402


def test_plan_via_route_builds_valid_multinode_plan():
    plan = plan_via_route("teach me a concept and quiz me on it", top=3)
    plan.validate()
    assert len(plan.nodes) >= 1
    # produced ids are unique; a chained node consumes the previous output.
    produces = [n.produces for n in plan.nodes]
    assert len(set(produces)) == len(produces)
    if len(plan.nodes) > 1:
        assert plan.nodes[1].inputs == [plan.nodes[0].produces]
        assert plan.nodes[1].depends_on == [plan.nodes[0].id]


def test_plan_via_manager_parses_json(monkeypatch):
    doc = {
        "schema": "plan/v1", "task_id": "m1", "goal": "g",
        "nodes": [{"id": "a", "agent": "teachAS", "prompt": "teach", "produces": "lesson",
                   "inputs": [], "depends_on": []}],
    }
    import json

    fake = FakeProvider(turns=[ProviderResponse(text="Here is the plan:\n```json\n" + json.dumps(doc) + "\n```")])
    plan = plan_via_manager("g", fake)
    assert isinstance(plan, Plan)
    assert plan.nodes[0].agent == "teachAS"


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(str(tmp_path / "run.db")))


def _wait(client, task_id, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = client.get(f"/api/tasks/{task_id}/status").json()["status"]
        if s in {"completed", "failed", "blocked"}:
            return s
        time.sleep(0.05)
    raise AssertionError("run did not finish")


def test_orchestrate_route_runs_multinode(client):
    resp = client.post("/api/orchestrate", json={"goal": "teach me eigenvalues then quiz me",
                                                 "planner": "route", "backend": "mock"})
    assert resp.status_code == 200
    body = resp.json()
    task_id = body["task_id"]
    assert body["plan"]["schema"] == "plan/v1"
    assert len(body["plan"]["nodes"]) >= 1

    assert _wait(client, task_id) == "completed"
    detail = client.get(f"/api/runs/{task_id}").json()
    assert detail["status"] == "completed"
    # graph exposes the produced artifacts for the DAG view
    graph = client.get(f"/api/runs/{task_id}/graph").json()
    assert any(n["kind"] == "artifact" for n in graph["nodes"])


def test_orchestrate_requires_goal(client):
    assert client.post("/api/orchestrate", json={}).status_code == 422
