"""Tests for the Immortals CLI (the orchestrator seam managerAS calls)."""

from __future__ import annotations

import json

from immortals.cli import main


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


def test_run_streams_per_agent_progress_to_stderr(capsys):
    """The 'deafening silence' fix: a default run narrates each agent's work on stderr, while
    stdout stays clean machine-readable JSON."""
    rc = main(["run", "--plan", _plan_json(), "--backend", "mock"])
    cap = capsys.readouterr()
    assert rc == 0
    assert json.loads(cap.out)["status"] == "completed"   # stdout unaffected
    assert "teachAS" in cap.err                            # the agent is named
    assert "[ok]" in cap.err                               # its completion is reflected
    assert "run complete" in cap.err
    assert "\\u" not in cap.err                            # ASCII-safe (no raw unicode escapes)


def test_run_quiet_suppresses_progress(capsys):
    rc = main(["run", "--plan", _plan_json(), "--backend", "mock", "--quiet"])
    cap = capsys.readouterr()
    assert rc == 0
    assert json.loads(cap.out)["status"] == "completed"
    assert cap.err.strip() == ""                           # no progress stream
