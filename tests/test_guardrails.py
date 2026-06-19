"""Tests for orchestrator guardrails + the approval gate (Phase 4, AS-005/AS-015)."""

from __future__ import annotations

import json

import pytest

from agentsuite.cli import main
from agentsuite.contracts.models import Node, Plan
from agentsuite.orchestrator import Guardrails, Orchestrator
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
    return Plan(task_id=f"t-{n}", goal="g", nodes=nodes)


class _TokenRunner(MockRunner):
    """MockRunner that stamps a fixed token cost into provenance."""

    def __init__(self, tokens_per_node: int):
        super().__init__()
        self._tokens = tokens_per_node

    def run(self, request):
        art = super().run(request)
        art.provenance = {**art.provenance, "cost": {"total_tokens": self._tokens}}
        return art


def test_no_guardrails_by_default(registry):
    assert not Guardrails().is_active()
    result = Orchestrator(runner=MockRunner(), registry=registry).run(_chain(3))
    assert result.status == "completed"


def test_max_nodes_halts_run(registry):
    mock = MockRunner()
    orch = Orchestrator(runner=mock, registry=registry, guardrails=Guardrails(max_nodes=2))
    result = orch.run(_chain(3))
    assert result.status == "failed"
    assert result.failed_node == "n2"
    assert [c.node_id for c in mock.calls] == ["n0", "n1"]
    assert any(e.get("payload", {}).get("reason") == "max_nodes_exceeded" for e in result.events)


def test_token_budget_halts_run(registry):
    orch = Orchestrator(runner=_TokenRunner(100), registry=registry,
                        guardrails=Guardrails(max_total_tokens=150))
    result = orch.run(_chain(3))
    # n0 spends 100 (ok), n1 spends 100 -> 200 > 150 -> halt after n1 produces.
    assert result.status == "failed"
    assert result.failed_node == "n1"
    assert any(e.get("payload", {}).get("reason") == "token_budget_exceeded" for e in result.events)


def test_wall_clock_budget_trips_in_state():
    # Direct, deterministic check of the state machine: elapsed beyond budget raises.
    from agentsuite.orchestrator.guardrails import GuardrailBreach, GuardrailState

    state = GuardrailState(Guardrails(max_wall_clock_s=1.0))
    state.before_node("teachAS", elapsed_s=0.5)  # within budget
    with pytest.raises(GuardrailBreach) as exc:
        state.before_node("teachAS", elapsed_s=1.5)  # over budget
    assert exc.value.reason == "wall_clock_exceeded"


def test_tokens_of_handles_missing_usage():
    from agentsuite.contracts.models import Artifact
    from agentsuite.orchestrator.guardrails import tokens_of

    bare = Artifact(id="a", produced_by="x", node_id="n", task_id="t", type="r", content={})
    assert tokens_of(bare) == 0
    with_cost = Artifact(id="a", produced_by="x", node_id="n", task_id="t", type="r",
                         content={}, provenance={"cost": {"total_tokens": 42}})
    assert tokens_of(with_cost) == 42


def test_max_agent_invocations_loop_guard(registry):
    mock = MockRunner()
    # All three nodes use teachAS; cap at 2 invocations of that agent.
    orch = Orchestrator(runner=mock, registry=registry,
                        guardrails=Guardrails(max_agent_invocations=2))
    result = orch.run(_chain(3))
    assert result.status == "failed"
    assert any(e.get("payload", {}).get("reason") == "agent_invocations_exceeded"
               for e in result.events)


def test_approval_required_without_handler_blocks(registry):
    plan = Plan(task_id="t-appr", goal="g",
                nodes=[Node(id="risky", agent="teachAS", prompt="p", produces="a",
                            approval="required", reversibility="irreversible")])
    mock = MockRunner()
    orch = Orchestrator(runner=mock, registry=registry)
    result = orch.run(plan)
    assert result.status == "blocked"
    assert result.failed_node == "risky"
    assert mock.calls == []  # never executed
    types = {e["type"] for e in result.events}
    assert "approval_requested" in types
    assert any(e.get("payload", {}).get("reason") == "approval_required" for e in result.events)


def test_approval_granted_proceeds(registry):
    plan = Plan(task_id="t-appr2", goal="g",
                nodes=[Node(id="risky", agent="teachAS", prompt="p", produces="a",
                            approval="required")])
    orch = Orchestrator(runner=MockRunner(), registry=registry,
                        approval_handler=lambda node: True)
    result = orch.run(plan)
    assert result.status == "completed"
    assert "a" in result.artifacts
    assert any(e["type"] == "approval_granted" for e in result.events)


def test_approval_denied_escalates(registry):
    plan = Plan(task_id="t-appr3", goal="g",
                nodes=[Node(id="risky", agent="teachAS", prompt="p", produces="a",
                            approval="required")])
    mock = MockRunner()
    orch = Orchestrator(runner=mock, registry=registry, approval_handler=lambda node: False)
    result = orch.run(plan)
    assert result.status == "blocked"
    assert mock.calls == []
    assert any(e.get("payload", {}).get("reason") == "approval_denied" for e in result.events)


# -- CLI surface --------------------------------------------------------------------------

def _plan_json(approval: str | None = None) -> str:
    node = {"id": "n", "agent": "teachAS", "prompt": "p", "produces": "out"}
    if approval:
        node["approval"] = approval
    return json.dumps({"schema": "plan/v1", "task_id": "cli-gr", "goal": "g", "nodes": [node]})


def test_cli_max_nodes_zero_fails(capsys):
    rc = main(["run", "--plan", _plan_json(), "--backend", "mock", "--max-nodes", "0", "--events"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["status"] == "failed"
    assert any(e.get("payload", {}).get("reason") == "max_nodes_exceeded" for e in out["events"])


def test_cli_approval_required_blocks_without_approve(capsys):
    rc = main(["run", "--plan", _plan_json(approval="required"), "--backend", "mock"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["status"] == "blocked"


def test_cli_approve_flag_grants(capsys):
    rc = main(["run", "--plan", _plan_json(approval="required"), "--backend", "mock", "--approve"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "completed"
