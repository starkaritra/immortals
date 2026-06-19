"""Tests for bounded parallel execution (--max-workers), Phase 5."""

from __future__ import annotations

import json
import threading
import time

import pytest

from agentsuite.cli import main
from agentsuite.contracts.models import Artifact, Node, Plan
from agentsuite.memory import MemoryStore
from agentsuite.orchestrator import Orchestrator
from agentsuite.registry import Registry
from agentsuite.runners import MockRunner
from agentsuite.runners.base import AgentRunner, RunRequest


@pytest.fixture
def registry():
    return Registry.load()


class _ConcurrencyProbe(AgentRunner):
    """Records peak concurrent invocations to prove (or disprove) real parallelism."""

    name = "probe"

    def __init__(self, delay: float = 0.05):
        self._delay = delay
        self._lock = threading.Lock()
        self.active = 0
        self.peak = 0

    def run(self, request: RunRequest) -> Artifact:
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(self._delay)
            return Artifact(id=request.produces, produced_by=request.agent,
                            node_id=request.node_id, task_id=request.task_id,
                            type="probe", content={"echo": request.prompt})
        finally:
            with self._lock:
                self.active -= 1


def _two_independent() -> Plan:
    return Plan(task_id="t-par", goal="g", nodes=[
        Node(id="a", agent="teachAS", prompt="p", produces="a.art"),
        Node(id="b", agent="paperAS", prompt="p", produces="b.art"),
    ])


def _diamond() -> Plan:
    # root -> {left, right} -> sink
    return Plan(task_id="t-diamond", goal="g", nodes=[
        Node(id="root", agent="experimentAS", prompt="p", produces="root.art"),
        Node(id="left", agent="teachAS", prompt="p", inputs=["root.art"], produces="left.art"),
        Node(id="right", agent="paperAS", prompt="p", inputs=["root.art"], produces="right.art"),
        Node(id="sink", agent="coderAS", prompt="p",
             inputs=["left.art", "right.art"], produces="sink.art"),
    ])


def test_independent_nodes_run_concurrently(registry):
    probe = _ConcurrencyProbe()
    result = Orchestrator(runner=probe, registry=registry, max_workers=2).run(_two_independent())
    assert result.status == "completed"
    assert set(result.artifacts) == {"a.art", "b.art"}
    assert probe.peak == 2  # both ran at the same time


def test_max_workers_one_is_sequential(registry):
    probe = _ConcurrencyProbe()
    result = Orchestrator(runner=probe, registry=registry, max_workers=1).run(_two_independent())
    assert result.status == "completed"
    assert probe.peak == 1  # never overlapped


def test_parallel_respects_dependencies(registry):
    probe = _ConcurrencyProbe()
    result = Orchestrator(runner=probe, registry=registry, max_workers=4).run(_diamond())
    assert result.status == "completed"
    assert set(result.artifacts) == {"root.art", "left.art", "right.art", "sink.art"}
    # The two middle nodes are independent and should overlap; sink/root cannot.
    assert probe.peak == 2

    # Dependency ordering holds in the event log: sink starts only after left & right complete.
    starts = {e["node_id"]: i for i, e in enumerate(result.events) if e["type"] == "node_started"}
    completes = {e["node_id"]: i for i, e in enumerate(result.events)
                 if e["type"] == "node_completed"}
    assert starts["left"] > completes["root"]
    assert starts["right"] > completes["root"]
    assert starts["sink"] > completes["left"]
    assert starts["sink"] > completes["right"]


def test_parallel_failure_reports_failing_node(registry):
    mock = MockRunner(fail_nodes={"b"})
    result = Orchestrator(runner=mock, registry=registry, max_workers=2).run(_two_independent())
    assert result.status == "failed"
    assert result.failed_node == "b"


def test_parallel_persists_to_store(registry):
    store = MemoryStore(":memory:")
    try:
        orch = Orchestrator(runner=_ConcurrencyProbe(), registry=registry, max_workers=4,
                            event_sink=store.append_event, artifact_sink=store.put_artifact)
        result = orch.run(_diamond())
        assert result.status == "completed"
        replay = store.reconstruct("t-diamond")
        assert replay.status == "completed"
        assert set(replay.artifacts) == {"root.art", "left.art", "right.art", "sink.art"}
    finally:
        store.close()


def test_parallel_guardrail_node_cap(registry):
    # Cap node executions at 2 across the diamond -> run fails once the cap is hit.
    from agentsuite.orchestrator import Guardrails

    orch = Orchestrator(runner=MockRunner(), registry=registry, max_workers=4,
                        guardrails=Guardrails(max_nodes=2))
    result = orch.run(_diamond())
    assert result.status == "failed"
    assert any(e.get("payload", {}).get("reason") == "max_nodes_exceeded" for e in result.events)


def test_cli_max_workers(capsys):
    plan = json.dumps({
        "schema": "plan/v1", "task_id": "cli-par", "goal": "g",
        "nodes": [
            {"id": "a", "agent": "teachAS", "prompt": "p", "produces": "a"},
            {"id": "b", "agent": "paperAS", "prompt": "p", "produces": "b"},
        ],
    })
    rc = main(["run", "--plan", plan, "--backend", "mock", "--max-workers", "2"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "completed"
    assert set(out["artifacts"]) == {"a", "b"}
