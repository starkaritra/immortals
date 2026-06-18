"""Tests for the AgentSuite CLI (the orchestrator seam managerAS calls)."""

from __future__ import annotations

import json

from agentsuite.cli import main


def _plan_json(agent: str = "teachAS") -> str:
    return json.dumps({
        "schema": "plan/v1",
        "task_id": "cli-t1",
        "goal": "explain X",
        "nodes": [{"id": "n", "agent": agent, "prompt": "explain X", "produces": "out"}],
    })


def test_run_mock_completes(capsys):
    rc = main(["run", "--plan", _plan_json(), "--backend", "mock"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "completed"
    assert "out" in out["artifacts"]
    assert out["artifacts"]["out"]["produced_by"] == "teachAS"


def test_run_invalid_json(capsys):
    rc = main(["run", "--plan", "{not json", "--backend", "mock"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert out["status"] == "failed"


def test_run_unregistered_agent_rejected(capsys):
    rc = main(["run", "--plan", _plan_json(agent="ghostAS"), "--backend", "mock"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert "plan rejected" in out["error"]


def test_run_with_events(capsys):
    rc = main(["run", "--plan", _plan_json(), "--backend", "mock", "--events"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert any(e["type"] == "run_completed" for e in out["events"])
