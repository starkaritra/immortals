"""Tests for the deterministic DAG orchestrator (using the MockRunner)."""

from __future__ import annotations

import pytest

from agentsuite.contracts.models import Plan, Node, Edge, Artifact
from agentsuite.orchestrator import Orchestrator
from agentsuite.orchestrator.runner import PlanError
from agentsuite.registry import Registry
from agentsuite.runners import MockRunner
from agentsuite.runners.base import AgentRunner, RunRequest, RunnerError


@pytest.fixture
def registry():
    return Registry.load()


def _single_node_plan() -> Plan:
    return Plan(
        task_id="t-single",
        goal="explain eigenvectors",
        nodes=[Node(id="teach", agent="teachAS", prompt="Explain eigenvectors.", produces="lesson")],
    )


def _two_node_plan() -> Plan:
    return Plan(
        task_id="t-chain",
        goal="design then write up",
        nodes=[
            Node(id="design", agent="experimentAS", prompt="Design the test.", produces="design.art"),
            Node(id="writeup", agent="paperAS", prompt="Write it up.",
                 inputs=["design.art"], produces="writeup.art"),
        ],
    )


def test_single_node_runs(registry):
    orch = Orchestrator(runner=MockRunner(), registry=registry)
    result = orch.run(_single_node_plan())
    assert result.status == "completed"
    assert "lesson" in result.artifacts
    assert {e["type"] for e in result.events} >= {"plan_validated", "node_completed", "run_completed"}


def test_chain_orders_by_dependency(registry):
    mock = MockRunner()
    orch = Orchestrator(runner=mock, registry=registry)
    result = orch.run(_two_node_plan())
    assert result.status == "completed"
    # design must run before writeup, and writeup receives design's artifact as input.
    assert [c.node_id for c in mock.calls] == ["design", "writeup"]
    writeup_call = mock.calls[1]
    assert "design.art" in writeup_call.inputs
    assert writeup_call.inputs["design.art"].produced_by == "experimentAS"


def test_failed_node_stops_and_escalates(registry):
    mock = MockRunner(fail_nodes={"design"})
    orch = Orchestrator(runner=mock, registry=registry)
    result = orch.run(_two_node_plan())
    assert result.status == "failed"
    assert result.failed_node == "design"
    assert any(e["type"] == "escalation" for e in result.events)
    # writeup must never run after design fails.
    assert [c.node_id for c in mock.calls] == ["design"]


def test_runner_error_escalates(registry):
    class BoomRunner(AgentRunner):
        name = "boom"
        def run(self, request: RunRequest):
            raise RunnerError("kaboom")

    orch = Orchestrator(runner=BoomRunner(), registry=registry)
    result = orch.run(_single_node_plan())
    assert result.status == "failed"
    assert result.error == "kaboom"


def test_unregistered_agent_rejected(registry):
    plan = Plan(task_id="t-x", goal="g",
                nodes=[Node(id="n", agent="ghostAS", prompt="p", produces="a")])
    orch = Orchestrator(runner=MockRunner(), registry=registry)
    with pytest.raises(PlanError):
        orch.run(plan)


def test_dangling_input_rejected(registry):
    plan = Plan(task_id="t-d", goal="g",
                nodes=[Node(id="n", agent="teachAS", prompt="p", inputs=["missing"], produces="a")])
    orch = Orchestrator(runner=MockRunner(), registry=registry)
    with pytest.raises(PlanError):
        orch.run(plan)


def test_cycle_rejected(registry):
    plan = Plan(
        task_id="t-cycle",
        goal="g",
        nodes=[
            Node(id="a", agent="teachAS", prompt="p", produces="x"),
            Node(id="b", agent="teachAS", prompt="p", produces="y"),
        ],
        edges=[Edge(from_="a", to="b"), Edge(from_="b", to="a")],
    )
    orch = Orchestrator(runner=MockRunner(), registry=registry)
    with pytest.raises(PlanError):
        orch.run(plan)


def test_seam_mismatch_fails(registry):
    class WrongIdRunner(AgentRunner):
        name = "wrong"
        def run(self, request: RunRequest):
            return Artifact(
                id="UNEXPECTED",  # does not match node.produces
                produced_by=request.agent,
                node_id=request.node_id,
                task_id=request.task_id,
                type="x",
                content={},
            )

    orch = Orchestrator(runner=WrongIdRunner(), registry=registry)
    result = orch.run(_single_node_plan())
    assert result.status == "failed"
    assert any(e.get("payload", {}).get("reason") == "contract_violation" for e in result.events)
