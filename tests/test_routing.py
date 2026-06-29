"""Tests for Phase 3 routing + the registry approval floor (AS-020)."""

from __future__ import annotations

import json

import pytest

from immortals.cli import main
from immortals.contracts.models import Node, Plan
from immortals.orchestrator import Orchestrator
from immortals.registry import Registry
from immortals.runners import MockRunner


@pytest.fixture
def registry():
    return Registry.load()


# -- Registry.route / describe -------------------------------------------------------------

def test_route_matches_capability_phrase(registry):
    ranked = registry.route("I need a rigorous experiment design with power analysis")
    assert ranked, "expected at least one candidate"
    assert ranked[0]["agent"] == "experimentAS"
    assert any(r.startswith("capability:") for r in ranked[0]["reasons"])


def test_route_for_teaching(registry):
    ranked = registry.route("explain this concept to me like a tutor")
    assert ranked[0]["agent"] == "teachAS"


def test_route_for_implementation(registry):
    ranked = registry.route("implement and debug this code, run the tests")
    assert ranked[0]["agent"] == "coderAS"


def test_route_is_deterministic_and_sorted(registry):
    a = registry.route("write a research paper")
    b = registry.route("write a research paper")
    assert a == b
    scores = [r["score"] for r in a]
    assert scores == sorted(scores, reverse=True)


def test_route_top_limit(registry):
    ranked = registry.route("design experiment analysis testing implementation", top=2)
    assert len(ranked) <= 2


def test_route_no_match_returns_empty(registry):
    assert registry.route("zzzzqqqq nonsense token xyz") == []


def test_describe_lists_all_agents(registry):
    described = registry.describe()
    assert {d["agent"] for d in described} == set(registry.agents())
    assert all("capabilities" in d and "approval_default" in d for d in described)


# -- Registry approval floor (opt-in) ------------------------------------------------------

def test_approval_floor_off_by_default(registry):
    # experimentAS has approval_default=required, but the floor is opt-in.
    plan = Plan(task_id="t", goal="g",
                nodes=[Node(id="n", agent="experimentAS", prompt="p", produces="a")])
    result = Orchestrator(runner=MockRunner(), registry=registry).run(plan)
    assert result.status == "completed"


def test_approval_floor_blocks_required_agent(registry):
    plan = Plan(task_id="t", goal="g",
                nodes=[Node(id="n", agent="experimentAS", prompt="p", produces="a")])
    orch = Orchestrator(runner=MockRunner(), registry=registry, enforce_registry_approval=True)
    result = orch.run(plan)
    assert result.status == "blocked"
    assert any(e["type"] == "approval_requested" for e in result.events)


def test_approval_floor_grants_with_handler(registry):
    plan = Plan(task_id="t", goal="g",
                nodes=[Node(id="n", agent="experimentAS", prompt="p", produces="a")])
    orch = Orchestrator(runner=MockRunner(), registry=registry,
                        enforce_registry_approval=True, approval_handler=lambda node: True)
    result = orch.run(plan)
    assert result.status == "completed"
    assert any(e["type"] == "approval_granted" for e in result.events)


def test_approval_floor_leaves_low_stakes_agents_alone(registry):
    # teachAS has approval_default=none → no gate even with enforcement on.
    plan = Plan(task_id="t", goal="g",
                nodes=[Node(id="n", agent="teachAS", prompt="p", produces="a")])
    orch = Orchestrator(runner=MockRunner(), registry=registry, enforce_registry_approval=True)
    result = orch.run(plan)
    assert result.status == "completed"
    assert not any(e["type"] == "approval_requested" for e in result.events)


# -- CLI -----------------------------------------------------------------------------------

def test_cli_agents_lists_catalogue(capsys):
    rc = main(["agents"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    agents = {a["agent"] for a in out["agents"]}
    assert {"experimentAS", "teachAS", "coderAS"} <= agents


def test_cli_route(capsys):
    rc = main(["route", "--need", "design a rigorous experiment"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["candidates"][0]["agent"] == "experimentAS"


def test_cli_route_no_match_exit_1(capsys):
    rc = main(["route", "--need", "zzzz nonsense qqqq"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["candidates"] == []


def test_cli_run_enforce_approvals_blocks(capsys):
    plan = json.dumps({
        "schema": "plan/v1", "task_id": "cli-appr-floor", "goal": "g",
        "nodes": [{"id": "n", "agent": "coderAS", "prompt": "p", "produces": "a"}],
    })
    rc = main(["run", "--plan", plan, "--backend", "mock", "--enforce-approvals"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["status"] == "blocked"
