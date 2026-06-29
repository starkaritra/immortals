"""Tests for the SQLite memory substrate (Phase 2, AS-006/007/014)."""

from __future__ import annotations

import json

import pytest

from immortals.cli import main
from immortals.contracts.models import Artifact, Node, Plan
from immortals.memory import MemoryStore
from immortals.orchestrator import Orchestrator
from immortals.registry import Registry
from immortals.runners import MockRunner


def _event(task_id: str, n: int, etype: str, **fields) -> dict:
    ev = {
        "schema": "event/v1",
        "event_id": f"{task_id}-{n}",
        "task_id": task_id,
        "ts": "2026-01-01T00:00:00Z",
        "type": etype,
    }
    ev.update(fields)
    return ev


def _artifact(task_id: str, art_id: str = "a1", status: str = "ok") -> Artifact:
    return Artifact(
        id=art_id,
        produced_by="teachAS",
        node_id="n1",
        task_id=task_id,
        type="mock_result",
        content={"echo": "hi"},
        status=status,
        provenance={"model": "mock", "ended": "2026-01-01T00:00:01Z"},
    )


@pytest.fixture
def store():
    s = MemoryStore(":memory:")
    yield s
    s.close()


def test_append_and_read_events(store):
    store.append_event(_event("t", 1, "plan_validated", payload={"nodes": 1}))
    store.append_event(_event("t", 2, "run_completed", payload={"artifacts": ["a1"]}))
    events = store.events_for("t")
    assert [e["type"] for e in events] == ["plan_validated", "run_completed"]
    assert events[0]["payload"] == {"nodes": 1}


def test_append_is_idempotent_on_event_id(store):
    store.append_event(_event("t", 1, "node_started", node_id="n1", agent="teachAS"))
    store.append_event(_event("t", 1, "node_started", node_id="n1", agent="teachAS"))
    assert len(store.events_for("t")) == 1


def test_invalid_event_rejected(store):
    bad = {"schema": "event/v1", "event_id": "x", "task_id": "t", "ts": "now", "type": "not_a_type"}
    with pytest.raises(Exception):
        store.append_event(bad)
    assert store.events_for("t") == []


def test_artifact_roundtrip(store):
    art = _artifact("t")
    store.put_artifact(art)
    got = store.get_artifact("t", "a1")
    assert got is not None
    assert got.to_dict() == art.to_dict()


def test_artifact_upsert(store):
    store.put_artifact(_artifact("t", status="partial"))
    store.put_artifact(_artifact("t", status="ok"))
    got = store.get_artifact("t", "a1")
    assert got.status == "ok"
    assert len(store.artifacts_for("t")) == 1


def test_events_are_append_only(store):
    store.append_event(_event("t", 1, "node_started", node_id="n1"))
    with pytest.raises(Exception):
        store._conn.execute("UPDATE events SET type='node_failed' WHERE event_id='t-1'")
    with pytest.raises(Exception):
        store._conn.execute("DELETE FROM events WHERE event_id='t-1'")


def test_reconstruct_completed(store):
    store.append_event(_event("t", 1, "plan_validated"))
    store.put_artifact(_artifact("t"))
    store.append_event(_event("t", 2, "artifact_written", node_id="n1", payload={"artifact_id": "a1"}))
    store.append_event(_event("t", 3, "run_completed"))
    res = store.reconstruct("t")
    assert res.status == "completed"
    assert "a1" in res.artifacts


def test_reconstruct_failed(store):
    store.append_event(_event("t", 1, "node_started", node_id="n1"))
    store.append_event(_event("t", 2, "node_failed", node_id="n1", payload={"error": "boom"}))
    res = store.reconstruct("t")
    assert res.status == "failed"
    assert res.failed_node == "n1"


def test_reconstruct_unknown_task_raises(store):
    with pytest.raises(KeyError):
        store.reconstruct("nope")


def test_tasks_listing(store):
    store.append_event(_event("alpha", 1, "plan_validated"))
    store.append_event(_event("beta", 1, "plan_validated"))
    assert store.tasks() == ["alpha", "beta"]


def test_orchestrator_persists_run(store):
    plan = Plan(
        task_id="t-chain",
        goal="g",
        nodes=[
            Node(id="design", agent="experimentAS", prompt="p", produces="design.art"),
            Node(id="write", agent="paperAS", prompt="p", inputs=["design.art"], produces="write.art"),
        ],
    )
    orch = Orchestrator(
        runner=MockRunner(),
        registry=Registry.load(),
        event_sink=store.append_event,
        artifact_sink=store.put_artifact,
    )
    result = orch.run(plan)
    assert result.status == "completed"

    # The persisted run reconstructs identically from the event log alone.
    replay = store.reconstruct("t-chain")
    assert replay.status == "completed"
    assert set(replay.artifacts) == {"design.art", "write.art"}
    assert any(e["type"] == "run_completed" for e in replay.events)
    # Every event the run emitted is durable.
    assert len(replay.events) == len(result.events)


def test_persistence_is_durable_across_connections(tmp_path):
    db = str(tmp_path / "mem.db")
    s1 = MemoryStore(db)
    s1.append_event(_event("t", 1, "plan_validated"))
    s1.put_artifact(_artifact("t"))
    s1.append_event(_event("t", 2, "run_completed"))
    s1.close()

    s2 = MemoryStore(db)
    res = s2.reconstruct("t")
    assert res.status == "completed"
    assert "a1" in res.artifacts
    s2.close()


def _plan_json() -> str:
    return json.dumps({
        "schema": "plan/v1",
        "task_id": "cli-mem",
        "goal": "explain X",
        "nodes": [{"id": "n", "agent": "teachAS", "prompt": "explain X", "produces": "out"}],
    })


def test_cli_run_db_then_replay(tmp_path, capsys):
    db = str(tmp_path / "cli.db")
    rc = main(["run", "--plan", _plan_json(), "--backend", "mock", "--db", db])
    assert rc == 0
    capsys.readouterr()

    rc = main(["replay", "--db", db, "--task-id", "cli-mem", "--events"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "completed"
    assert "out" in out["artifacts"]
    assert any(e["type"] == "run_completed" for e in out["events"])


def test_cli_replay_list(tmp_path, capsys):
    db = str(tmp_path / "cli.db")
    main(["run", "--plan", _plan_json(), "--backend", "mock", "--db", db])
    capsys.readouterr()
    rc = main(["replay", "--db", db, "--list"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["tasks"] == ["cli-mem"]
