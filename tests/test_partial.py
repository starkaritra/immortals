"""Tests for partial re-runs (--from / --to), Phase 5."""

from __future__ import annotations

import json

import pytest

from agentsuite.cli import main
from agentsuite.contracts.models import Node, Plan
from agentsuite.memory import MemoryStore
from agentsuite.orchestrator import Orchestrator
from agentsuite.orchestrator.runner import PlanError
from agentsuite.registry import Registry
from agentsuite.runners import MockRunner


@pytest.fixture
def registry():
    return Registry.load()


def _diamond() -> Plan:
    # root -> {left, right} -> sink
    return Plan(task_id="t-diamond", goal="g", nodes=[
        Node(id="root", agent="experimentAS", prompt="p", produces="root.art"),
        Node(id="left", agent="teachAS", prompt="p", inputs=["root.art"], produces="left.art"),
        Node(id="right", agent="paperAS", prompt="p", inputs=["root.art"], produces="right.art"),
        Node(id="sink", agent="coderAS", prompt="p",
             inputs=["left.art", "right.art"], produces="sink.art"),
    ])


def _executed(mock: MockRunner) -> set[str]:
    return {c.node_id for c in mock.calls}


def test_to_runs_only_target_and_ancestors(registry):
    mock = MockRunner()
    result = Orchestrator(runner=mock, registry=registry).run(_diamond(), to_node="left")
    assert result.status == "completed"
    # left + its ancestor root; right and sink are out of scope.
    assert _executed(mock) == {"root", "left"}
    assert set(result.artifacts) == {"root.art", "left.art"}


def test_to_emits_partial_decision_event(registry):
    result = Orchestrator(runner=MockRunner(), registry=registry).run(_diamond(), to_node="left")
    decision = [e for e in result.events if e["type"] == "decision"]
    assert decision and decision[0]["payload"]["partial_run"]["selected"] == ["left", "root"]


def test_from_runs_node_and_descendants_with_seed(registry):
    plan = _diamond()
    store = MemoryStore(":memory:")
    try:
        # Full run first so upstream artifacts (root, right) are persisted.
        Orchestrator(runner=MockRunner(), registry=registry,
                     event_sink=store.append_event, artifact_sink=store.put_artifact).run(plan)

        mock = MockRunner()
        result = Orchestrator(runner=mock, registry=registry,
                              event_sink=store.append_event,
                              artifact_sink=store.put_artifact).run(
            plan, resume_from=store.artifacts_for("t-diamond"), from_node="left")
        assert result.status == "completed"
        # from=left selects {left, sink}; sink also needs right.art, sourced from the seed.
        assert _executed(mock) == {"left", "sink"}
        assert set(result.artifacts) >= {"left.art", "sink.art", "right.art", "root.art"}
    finally:
        store.close()


def test_from_to_slice(registry):
    mock = MockRunner()
    # from=root to=left -> only the path root..left.
    result = Orchestrator(runner=mock, registry=registry).run(
        _diamond(), from_node="root", to_node="left")
    assert result.status == "completed"
    assert _executed(mock) == {"root", "left"}


def test_from_without_seed_raises(registry):
    # from=sink needs left.art/right.art, but nothing is seeded -> PlanError.
    with pytest.raises(PlanError):
        Orchestrator(runner=MockRunner(), registry=registry).run(_diamond(), from_node="sink")


def test_unknown_from_node_raises(registry):
    with pytest.raises(PlanError):
        Orchestrator(runner=MockRunner(), registry=registry).run(_diamond(), from_node="ghost")


def test_partial_reruns_overwrite_artifact(registry):
    plan = _diamond()
    store = MemoryStore(":memory:")
    try:
        # First full run stamps content {"echo": "p"} everywhere.
        Orchestrator(runner=MockRunner(), registry=registry,
                     event_sink=store.append_event, artifact_sink=store.put_artifact).run(plan)
        # Re-run just `left` with a responder that changes its content.
        responder = lambda req: {"echo": "RERUN"}
        Orchestrator(runner=MockRunner(responder=responder), registry=registry,
                     event_sink=store.append_event, artifact_sink=store.put_artifact).run(
            plan, resume_from=store.artifacts_for("t-diamond"), from_node="left", to_node="left")
        # left.art is overwritten in the store with the new content.
        assert store.get_artifact("t-diamond", "left.art").content == {"echo": "RERUN"}
        # root.art (untouched) keeps the original content.
        assert store.get_artifact("t-diamond", "root.art").content == {"echo": "p"}
    finally:
        store.close()


# -- CLI -----------------------------------------------------------------------------------

def _diamond_json() -> str:
    return json.dumps({
        "schema": "plan/v1", "task_id": "cli-partial", "goal": "g",
        "nodes": [
            {"id": "root", "agent": "experimentAS", "prompt": "p", "produces": "root.art"},
            {"id": "left", "agent": "teachAS", "prompt": "p", "inputs": ["root.art"], "produces": "left.art"},
            {"id": "right", "agent": "paperAS", "prompt": "p", "inputs": ["root.art"], "produces": "right.art"},
            {"id": "sink", "agent": "coderAS", "prompt": "p",
             "inputs": ["left.art", "right.art"], "produces": "sink.art"},
        ],
    })


def test_cli_to_without_db(capsys):
    rc = main(["run", "--plan", _diamond_json(), "--backend", "mock", "--to", "left"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "completed"
    assert set(out["artifacts"]) == {"root.art", "left.art"}


def test_cli_from_requires_db(capsys):
    rc = main(["run", "--plan", _diamond_json(), "--backend", "mock", "--from", "left"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "--from requires --db" in out["error"]


def test_cli_full_then_partial_from(tmp_path, capsys):
    db = str(tmp_path / "partial.db")
    main(["run", "--plan", _diamond_json(), "--backend", "mock", "--db", db])
    capsys.readouterr()
    rc = main(["run", "--plan", _diamond_json(), "--backend", "mock", "--db", db, "--from", "left"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "completed"
