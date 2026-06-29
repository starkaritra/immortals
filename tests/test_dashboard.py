"""Tests for the read-only dashboard (prototype frontend).

These exercise the endpoint **data shaping** against a real in-memory store, not the HTML. The whole
module is skipped when the optional ``[dashboard]`` extra (FastAPI + httpx) is absent, so the core
test suite stays green without it.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="dashboard extra not installed")
pytest.importorskip("httpx", reason="fastapi TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from immortals.contracts.models import Artifact  # noqa: E402
from immortals.dashboard.app import create_app, run_summary  # noqa: E402
from immortals.memory import MemoryStore  # noqa: E402

TASK = "demo-task"


def _seed(db_path: str) -> None:
    """Write a tiny but realistic two-node run (lesson → quiz) straight to the store."""
    store = MemoryStore(db_path)
    ev = lambda eid, typ, **kw: store.append_event(  # noqa: E731
        {"schema": "event/v1", "event_id": eid, "task_id": TASK, "ts": "2026-06-27T10:00:00", "type": typ, **kw})
    ev("e1", "plan_validated")
    ev("e2", "node_started", node_id="lesson", agent="teachAS")
    store.put_artifact(Artifact(
        id="lesson", produced_by="teachAS", node_id="lesson", task_id=TASK,
        type="mock_result", content={"echo": "what eigenvectors are"},
        provenance={"model": "mock", "inputs": [], "cost": {"total_tokens": 100}}))
    ev("e3", "artifact_written", node_id="lesson")
    ev("e4", "node_completed", node_id="lesson")
    ev("e5", "node_started", node_id="quiz", agent="teachAS")
    store.put_artifact(Artifact(
        id="quiz", produced_by="teachAS", node_id="quiz", task_id=TASK,
        type="mock_result", content={"echo": "a quiz on the lesson"},
        provenance={"model": "mock", "inputs": ["lesson"], "cost": {"total_tokens": 50}}))
    ev("e6", "artifact_written", node_id="quiz")
    ev("e7", "node_completed", node_id="quiz")
    ev("e8", "run_completed")
    store.close()


@pytest.fixture
def client(tmp_path):
    db = tmp_path / "run.db"
    _seed(str(db))
    return TestClient(create_app(str(db)))


def test_runs_list_summarizes(client):
    data = client.get("/api/runs").json()
    assert [t["task_id"] for t in data["tasks"]] == [TASK]
    row = data["tasks"][0]
    assert row["status"] == "completed"
    assert row["node_count"] == 2
    assert row["artifact_count"] == 2
    assert row["total_tokens"] == 150  # 100 + 50, summed from provenance.cost


def test_run_detail_shape(client):
    data = client.get(f"/api/runs/{TASK}").json()
    assert data["status"] == "completed"
    assert set(data["artifacts"]) == {"lesson", "quiz"}
    assert data["artifacts"]["lesson"]["schema"] == "artifact/v1"
    assert len(data["events"]) == 8
    assert "failed_node" not in data


def test_run_detail_missing_is_404(client):
    assert client.get("/api/runs/nope").status_code == 404


def test_run_graph_has_depends_on(client):
    g = client.get(f"/api/runs/{TASK}/graph").json()
    rels = {e["rel"] for e in g["edges"]}
    assert "depends_on" in rels  # quiz depends_on lesson (provenance.inputs)
    assert any(n["kind"] == "artifact" for n in g["nodes"])


def test_artifact_viewer(client):
    a = client.get(f"/api/artifacts/{TASK}/lesson").json()
    assert a["id"] == "lesson"
    assert a["produced_by"] == "teachAS"
    assert a["provenance"]["cost"]["total_tokens"] == 100


def test_artifact_missing_is_404(client):
    assert client.get(f"/api/artifacts/{TASK}/ghost").status_code == 404


def test_recall_ranks_hits(client):
    data = client.get("/api/recall", params={"q": "eigenvectors", "top": 5}).json()
    assert data["query"] == "eigenvectors"
    assert isinstance(data["hits"], list)
    assert all("ref_id" in h and "score" in h for h in data["hits"])


def test_recall_requires_query(client):
    assert client.get("/api/recall").status_code == 422  # missing required q


def test_graph_endpoint(client):
    g = client.get("/api/graph").json()
    assert "nodes" in g and "edges" in g


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Immortals" in r.text


def test_run_summary_helper_directly(tmp_path):
    db = tmp_path / "r.db"
    _seed(str(db))
    store = MemoryStore(str(db))
    try:
        s = run_summary(store, TASK)
        assert s["total_tokens"] == 150 and s["node_count"] == 2
    finally:
        store.close()
