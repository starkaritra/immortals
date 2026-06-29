"""Tests for CopilotRunner JSONL parsing + usage capture (Backend A, AS-018).

These exercise the pure parser (no subprocess / no real LLM call); the live end-to-end check is
``scripts/smoke_backend_a.py``.
"""

from __future__ import annotations

import json

from immortals.runners import CopilotRunner


def _jsonl(*objs: dict) -> str:
    return "\n".join(json.dumps(o) for o in objs)


def test_parse_jsonl_sums_tokens_and_takes_final_response():
    stdout = _jsonl(
        {"type": "session.mcp_servers_loaded", "data": {}},
        {"type": "user.message", "data": {"content": "hi"}},
        # An intermediate tool-using assistant message (counts toward tokens, not the answer).
        {"type": "assistant.message",
         "data": {"model": "claude-opus-4.8", "content": "", "outputTokens": 12,
                  "toolRequests": [{"name": "shell"}]}},
        {"type": "assistant.message",
         "data": {"model": "claude-opus-4.8", "content": "the final answer", "outputTokens": 8}},
        {"type": "assistant.turn_end", "data": {}},
        {"type": "result", "timestamp": "t", "sessionId": "sess-123", "exitCode": 0,
         "usage": {"premiumRequests": 3, "totalApiDurationMs": 1870, "sessionDurationMs": 13017}},
    )
    parsed = CopilotRunner._parse_jsonl(stdout)
    assert parsed["response"] == "the final answer"
    assert parsed["output_tokens"] == 20  # 12 + 8
    assert parsed["model"] == "claude-opus-4.8"
    assert parsed["premium_requests"] == 3
    assert parsed["session_id"] == "sess-123"
    assert parsed["result_exit"] == 0


def test_parse_jsonl_skips_non_json_lines():
    stdout = "not json at all\n" + _jsonl(
        {"type": "assistant.message", "data": {"content": "ok", "outputTokens": 5}},
        {"type": "result", "exitCode": 0, "usage": {}},
    )
    parsed = CopilotRunner._parse_jsonl(stdout)
    assert parsed["response"] == "ok"
    assert parsed["output_tokens"] == 5


def test_parse_jsonl_no_usage_is_none():
    stdout = _jsonl({"type": "assistant.message", "data": {"content": "hi"}})
    parsed = CopilotRunner._parse_jsonl(stdout)
    assert parsed["response"] == "hi"
    assert parsed["output_tokens"] is None  # no outputTokens reported → no token charge


def test_parse_jsonl_empty_output():
    parsed = CopilotRunner._parse_jsonl("")
    assert parsed["response"] == ""
    assert parsed["output_tokens"] is None
    assert parsed["result_exit"] is None


def test_command_uses_json_output_not_silent():
    runner = CopilotRunner()
    from immortals.runners.base import RunRequest
    req = RunRequest(agent="teachAS", node_id="n", task_id="t", prompt="p", produces="a")
    cmd = runner._build_command(req, "p")
    assert "--output-format" in cmd and "json" in cmd
    assert "-s" not in cmd
    assert "--no-ask-user" in cmd


def test_parsed_tokens_feed_the_guardrail():
    """The parser's token total flows into provenance.cost.total_tokens, which the guardrail reads."""
    from immortals.contracts.models import Artifact
    from immortals.orchestrator.guardrails import tokens_of

    parsed = CopilotRunner._parse_jsonl(_jsonl(
        {"type": "assistant.message", "data": {"content": "x", "outputTokens": 42}},
        {"type": "result", "exitCode": 0, "usage": {}},
    ))
    art = Artifact(id="a", produced_by="teachAS", node_id="n", task_id="t", type="agent_response",
                   content={"response": parsed["response"]},
                   provenance={"cost": {"total_tokens": parsed["output_tokens"]}})
    assert tokens_of(art) == 42


def test_run_records_input_ids_in_provenance(monkeypatch):
    """Regression: the copilot backend must record provenance.inputs (the source of the derived
    graph's depends_on edges) — like MockRunner. Without it, real runs render an edge-less DAG."""
    import subprocess
    from types import SimpleNamespace

    from immortals.contracts.models import Artifact
    from immortals.runners import copilot_backend
    from immortals.runners.base import RunRequest

    upstream = Artifact(id="lesson", produced_by="teachAS", node_id="n0", task_id="t",
                        type="agent_response", content={"response": "x"})
    req = RunRequest(agent="teachAS", node_id="n1", task_id="t", prompt="p", produces="quiz",
                     inputs={"lesson": upstream})

    monkeypatch.setattr(copilot_backend.shutil, "which", lambda _: "copilot")
    fake = SimpleNamespace(
        stdout=_jsonl({"type": "assistant.message", "data": {"content": "done", "outputTokens": 3}},
                      {"type": "result", "exitCode": 0, "usage": {}}),
        stderr="", returncode=0)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)

    art = copilot_backend.CopilotRunner().run(req)
    assert art.provenance["inputs"] == ["lesson"]
