"""Tests for the AgentSuite JSON contracts and ergonomic models."""

from __future__ import annotations

import pytest

from agentsuite.contracts import validate, is_valid, ContractError, validate_self_described
from agentsuite.contracts.models import Plan, Node, Edge, Artifact


# --- fixtures -------------------------------------------------------------------------

def _valid_plan() -> dict:
    return {
        "schema": "plan/v1",
        "task_id": "t1",
        "goal": "Validate a caching idea and write it up.",
        "objective": "Confirm the cache improves p95 latency without raising error rate.",
        "key_results": ["p95 down >=10%", "error rate flat"],
        "nodes": [
            {
                "id": "design",
                "agent": "experimentAS",
                "prompt": "Design an A/B test for the cache.",
                "produces": "design.artifact",
                "success_criteria": "A pre-registered, powered design.",
                "reversibility": "reversible",
                "approval": "required",
                "budget": {"max_tokens": 40000, "timeout_s": 600},
            },
            {
                "id": "writeup",
                "agent": "paperAS",
                "prompt": "Write up the result.",
                "inputs": ["design.artifact"],
                "produces": "writeup.artifact",
            },
        ],
        "edges": [{"from": "design", "to": "writeup", "on": "success"}],
    }


def _valid_artifact() -> dict:
    return {
        "schema": "artifact/v1",
        "id": "design.artifact",
        "produced_by": "experimentAS",
        "node_id": "design",
        "task_id": "t1",
        "type": "experiment_design",
        "content": {"hypothesis": "cache lowers p95"},
        "status": "ok",
        "untrusted": True,
    }


def _valid_manifest() -> dict:
    return {
        "schema": "registry/v1",
        "agent": "experimentAS",
        "summary": "Designs/conducts/analyzes rigorous experiments.",
        "capabilities": ["experiment_design", "statistical_analysis"],
        "consumes": ["hypothesis", "dataset_ref"],
        "produces": ["experiment_design", "analysis_report"],
        "approval_default": "required",
        "cost_hint": "medium",
        "when_to_use": "validate or verify a hypothesis, product, or design choice",
    }


def _valid_event() -> dict:
    return {
        "schema": "event/v1",
        "event_id": "e1",
        "task_id": "t1",
        "ts": "2026-06-18T12:00:00+05:30",
        "type": "node_started",
        "node_id": "design",
        "agent": "experimentAS",
        "payload": {"prompt_len": 42},
    }


# --- happy path -----------------------------------------------------------------------

@pytest.mark.parametrize(
    "instance,contract",
    [
        (_valid_plan(), "plan/v1"),
        (_valid_artifact(), "artifact/v1"),
        (_valid_manifest(), "registry/v1"),
        (_valid_event(), "event/v1"),
    ],
)
def test_valid_instances_pass(instance, contract):
    validate(instance, contract)  # must not raise
    assert is_valid(instance, contract)
    assert validate_self_described(instance) == contract


# --- rejection cases ------------------------------------------------------------------

def test_plan_requires_nodes():
    plan = _valid_plan()
    plan["nodes"] = []
    with pytest.raises(ContractError):
        validate(plan, "plan/v1")


def test_plan_rejects_unknown_field():
    plan = _valid_plan()
    plan["nodes"][0]["unexpected"] = True
    with pytest.raises(ContractError):
        validate(plan, "plan/v1")


def test_plan_rejects_bad_enum():
    plan = _valid_plan()
    plan["nodes"][0]["approval"] = "maybe"
    assert not is_valid(plan, "plan/v1")


def test_node_requires_produces():
    plan = _valid_plan()
    del plan["nodes"][0]["produces"]
    with pytest.raises(ContractError):
        validate(plan, "plan/v1")


def test_artifact_requires_status():
    art = _valid_artifact()
    del art["status"]
    with pytest.raises(ContractError):
        validate(art, "artifact/v1")


def test_artifact_rejects_bad_status():
    art = _valid_artifact()
    art["status"] = "great"
    assert not is_valid(art, "artifact/v1")


def test_manifest_requires_capabilities():
    m = _valid_manifest()
    m["capabilities"] = []
    with pytest.raises(ContractError):
        validate(m, "registry/v1")


def test_event_rejects_unknown_type():
    e = _valid_event()
    e["type"] = "exploded"
    assert not is_valid(e, "event/v1")


def test_unknown_contract_raises():
    with pytest.raises(KeyError):
        validate({}, "nonsense/v9")


# --- model round-trips ----------------------------------------------------------------

def test_plan_model_roundtrip():
    plan = Plan.from_dict(_valid_plan())
    again = Plan.from_dict(plan.to_dict())
    assert again.to_dict() == plan.to_dict()
    plan.validate()
    assert plan.node("design").agent == "experimentAS"


def test_plan_model_build_and_validate():
    plan = Plan(
        task_id="t2",
        goal="teach me eigenvectors",
        nodes=[Node(id="teach", agent="teachAS", prompt="explain eigenvectors", produces="lesson")],
    )
    plan.validate()
    assert plan.to_dict()["nodes"][0]["produces"] == "lesson"


def test_artifact_model_roundtrip():
    art = Artifact.from_dict(_valid_artifact())
    assert Artifact.from_dict(art.to_dict()).to_dict() == art.to_dict()


def test_edge_from_dict_uses_from_keyword():
    e = Edge.from_dict({"from": "a", "to": "b"})
    assert e.from_ == "a" and e.to == "b" and e.on == "success"
