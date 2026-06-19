"""Tests for --resume: skip already-completed nodes from the event-sourced store (Phase 5)."""

from __future__ import annotations

import json

import pytest

from agentsuite.cli import main
from agentsuite.contracts.models import Node, Plan
from agentsuite.memory import MemoryStore
from agentsuite.orchestrator import Orchestrator
from agentsuite.registry import Registry
from agentsuite.runners import MockRunner


@pytest.fixture
def registry():
    return Registry.load()


def _chain(n: int = 3) -> Plan:
    nodes = []
    prev = None
    for i in range(n):
        inputs = [prev] if prev else []
        nodes.append(Node(id=f"n{i}", agent="teachAS", prompt="p",
                          produces=f"a{i}", inputs=inputs))
        prev = f"a{i}"
    return Plan(task_id="t-resume", goal="g", nodes=nodes)


def test_resume_skips_seeded_node(registry):
    plan = _chain(2)
    # Run once to obtain n0's real artifact.
    first = Orchestrator(runner=MockRunner(), registry=registry).run(plan)
    seed = {"a0": first.artifacts["a0"]}

    mock = MockRunner()
    result = Orchestrator(runner=mock, registry=registry).run(plan, resume_from=seed)
    assert result.status == "completed"
    # n0 was seeded → its runner is never called; only n1 runs.
    assert [c.node_id for c in mock.calls] == ["n1"]
    # The skipped node is recorded as a resumed completion.
    assert any(e["type"] == "node_completed" and e.get("payload", {}).get("skipped") == "resumed"
               for e in result.events)
    assert set(result.artifacts) == {"a0", "a1"}


def test_resume_after_failure_completes_remaining(registry):
    plan = _chain(3)
    store = MemoryStore(":memory:")
    try:
        # First attempt: n1 fails; only n0 is persisted (failed artifacts are not stored).
        failing = MockRunner(fail_nodes={"n1"})
        r1 = Orchestrator(
            runner=failing, registry=registry,
            event_sink=store.append_event, artifact_sink=store.put_artifact,
        ).run(plan)
        assert r1.status == "failed"
        assert set(store.artifacts_for("t-resume")) == {"a0"}

        # Resume with a healthy runner: n0 skipped, n1+n2 execute → completed.
        healthy = MockRunner()
        r2 = Orchestrator(
            runner=healthy, registry=registry,
            event_sink=store.append_event, artifact_sink=store.put_artifact,
        ).run(plan, resume_from=store.artifacts_for("t-resume"))
        assert r2.status == "completed"
        assert [c.node_id for c in healthy.calls] == ["n1", "n2"]

        # The persisted run now reconstructs as a completed 3-artifact run.
        replay = store.reconstruct("t-resume")
        assert replay.status == "completed"
        assert set(replay.artifacts) == {"a0", "a1", "a2"}
    finally:
        store.close()


def test_resume_event_ids_do_not_collide(registry):
    """A resumed run reuses the same task_id; events must still be uniquely id'd and durable."""
    plan = _chain(2)
    store = MemoryStore(":memory:")
    try:
        orch = Orchestrator(runner=MockRunner(), registry=registry,
                            event_sink=store.append_event, artifact_sink=store.put_artifact)
        orch.run(plan)
        n_after_first = len(store.events_for("t-resume"))
        # Re-run (resume) — a second plan_validated + skipped completions must all persist.
        orch.run(plan, resume_from=store.artifacts_for("t-resume"))
        assert len(store.events_for("t-resume")) > n_after_first
    finally:
        store.close()


# -- CLI: interrupt with --max-nodes, then --resume to finish ------------------------------

def _plan_json() -> str:
    return json.dumps({
        "schema": "plan/v1",
        "task_id": "cli-resume",
        "goal": "g",
        "nodes": [
            {"id": "n0", "agent": "experimentAS", "prompt": "p", "produces": "a0"},
            {"id": "n1", "agent": "paperAS", "prompt": "p", "inputs": ["a0"], "produces": "a1"},
        ],
    })


def test_cli_resume_requires_db(capsys):
    rc = main(["run", "--plan", _plan_json(), "--backend", "mock", "--resume"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "requires --db" in out["error"]


def test_cli_interrupt_then_resume(tmp_path, capsys):
    db = str(tmp_path / "resume.db")

    # Interrupt the run after the first node via a node-count cap.
    rc = main(["run", "--plan", _plan_json(), "--backend", "mock", "--db", db, "--max-nodes", "1"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["status"] == "failed"

    # Resume (no cap): n0 is skipped, n1 completes → run completes.
    rc = main(["run", "--plan", _plan_json(), "--backend", "mock", "--db", db, "--resume", "--events"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "completed"
    assert set(out["artifacts"]) == {"a0", "a1"}
    assert any(e["type"] == "node_completed" and e.get("payload", {}).get("skipped") == "resumed"
               for e in out["events"])
