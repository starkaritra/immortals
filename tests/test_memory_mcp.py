"""Tests for the memory MCP server, the notes KV, and worker-memory injection (AS-021)."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from agentsuite.contracts.models import Artifact
from agentsuite.memory import MemoryStore
from agentsuite.memory import mcp_server as srv
from agentsuite.runners import CopilotRunner
from agentsuite.runners.base import RunRequest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def store():
    s = MemoryStore(":memory:")
    yield s
    s.close()


def _artifact(task_id: str, art_id: str = "a1") -> Artifact:
    return Artifact(id=art_id, produced_by="teachAS", node_id="n", task_id=task_id,
                    type="agent_response", content={"response": "hi"})


# -- notes KV (store) ----------------------------------------------------------------------

def test_notes_roundtrip(store):
    store.put_note("t", "scratch", {"step": 1, "done": False}, agent="experimentAS")
    assert store.get_note("t", "scratch") == {"step": 1, "done": False}
    notes = store.notes_for("t")
    assert notes["scratch"]["agent"] == "experimentAS"
    assert notes["scratch"]["value"] == {"step": 1, "done": False}


def test_notes_upsert(store):
    store.put_note("t", "k", "v1")
    store.put_note("t", "k", "v2")
    assert store.get_note("t", "k") == "v2"
    assert len(store.notes_for("t")) == 1


def test_get_missing_note_is_none(store):
    assert store.get_note("t", "nope") is None


def test_v1_store_migrates_to_v2_notes(tmp_path):
    db = str(tmp_path / "legacy.db")
    # Simulate a pre-notes (v1) database: real schema minus the notes table, user_version=1.
    s = MemoryStore(db)
    s._conn.execute("DROP TABLE notes")
    s._conn.execute("PRAGMA user_version = 1")
    s._conn.commit()
    s.close()
    # Reopening must migrate it forward and create the notes table.
    s2 = MemoryStore(db)
    try:
        s2.put_note("t", "k", "v")
        assert s2.get_note("t", "k") == "v"
        assert s2._conn.execute("PRAGMA user_version").fetchone()[0] == 2
    finally:
        s2.close()


# -- MCP dispatch / tools ------------------------------------------------------------------

def test_initialize_and_tools_list(store):
    init = srv.dispatch(store, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["serverInfo"]["name"] == "agentsuite-memory"
    listed = srv.dispatch(store, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in listed["result"]["tools"]}
    assert names == {
        "memory_get_artifact", "memory_list_artifacts", "memory_put_note",
        "memory_get_note", "memory_list_notes", "memory_recent_events",
    }


def test_tool_put_then_get_note(store):
    text, err = srv.call_tool(store, "memory_put_note",
                              {"task_id": "t", "key": "plan", "value": "do X", "agent": "coderAS"})
    assert err is False
    text, err = srv.call_tool(store, "memory_get_note", {"task_id": "t", "key": "plan"})
    assert err is False
    assert json.loads(text) == "do X"


def test_tool_list_artifacts(store):
    store.put_artifact(_artifact("t"))
    text, err = srv.call_tool(store, "memory_list_artifacts", {"task_id": "t"})
    assert err is False
    assert "a1" in json.loads(text)


def test_tool_recent_events_limit(store):
    for i in range(5):
        store.append_event({"schema": "event/v1", "event_id": f"t-{i}", "task_id": "t",
                            "ts": "now", "type": "node_started"})
    text, _ = srv.call_tool(store, "memory_recent_events", {"task_id": "t", "limit": 2})
    assert len(json.loads(text)) == 2


def test_tool_missing_required_arg_errors(store):
    text, err = srv.call_tool(store, "memory_get_note", {"task_id": "t"})
    assert err is True
    assert "missing required" in json.loads(text)["error"]


def test_dispatch_unknown_tool_errors(store):
    resp = srv.dispatch(store, {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                                "params": {"name": "memory_nope", "arguments": {}}})
    assert resp["error"]["code"] == -32602


def test_dispatch_notification_returns_none(store):
    assert srv.dispatch(store, {"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


# -- injection into the worker command -----------------------------------------------------

def test_runner_injects_mcp_config():
    runner = CopilotRunner(mcp_config='{"mcpServers": {}}')
    req = RunRequest(agent="teachAS", node_id="n", task_id="t", prompt="p", produces="a")
    cmd = runner._build_command(req, "p")
    assert "--additional-mcp-config" in cmd
    assert cmd[cmd.index("--additional-mcp-config") + 1] == '{"mcpServers": {}}'


def test_runner_omits_mcp_config_when_unset():
    runner = CopilotRunner()
    req = RunRequest(agent="teachAS", node_id="n", task_id="t", prompt="p", produces="a")
    assert "--additional-mcp-config" not in runner._build_command(req, "p")


def test_server_resolves_db_from_arg_and_env(monkeypatch):
    assert srv._resolve_db(["--db", "C:/x.db"]) == "C:/x.db"
    assert srv._resolve_db(["--db=C:/y.db"]) == "C:/y.db"
    monkeypatch.setenv("AGENTSUITE_MEMORY_DB", "C:/from-env.db")
    assert srv._resolve_db([]) == "C:/from-env.db"
    monkeypatch.delenv("AGENTSUITE_MEMORY_DB", raising=False)
    # Falls back to a stable default (so a persistently-registered server never errors).
    fallback = srv._resolve_db([])
    assert fallback.endswith("memory.db") and ".copilot" in fallback


def test_runner_stores_env_extra():
    runner = CopilotRunner(env_extra={"AGENTSUITE_MEMORY_DB": "C:/run.db"})
    assert runner.env_extra["AGENTSUITE_MEMORY_DB"] == "C:/run.db"


# -- persistent registration command -------------------------------------------------------

def test_memory_register_preserves_other_servers(tmp_path):
    cfg = tmp_path / "mcp-config.json"
    cfg.write_text(json.dumps({"mcpServers": {"kgraph": {"type": "local", "command": "python"}}}),
                   encoding="utf-8")
    from agentsuite.cli import main as cli_main
    rc = cli_main(["memory", "register", "--config-path", str(cfg)])
    assert rc == 0
    data = json.loads(cfg.read_text())
    assert "kgraph" in data["mcpServers"]                      # untouched
    entry = data["mcpServers"]["agentsuite-memory"]
    assert entry["args"] == ["-m", "agentsuite.memory.mcp_server"]
    assert entry["tools"] == ["*"]


def test_memory_register_then_unregister(tmp_path, capsys):
    cfg = tmp_path / "mcp-config.json"
    from agentsuite.cli import main as cli_main
    cli_main(["memory", "register", "--config-path", str(cfg)])
    capsys.readouterr()
    cli_main(["memory", "status", "--config-path", str(cfg)])
    assert json.loads(capsys.readouterr().out)["registered"] is True
    cli_main(["memory", "unregister", "--config-path", str(cfg)])
    capsys.readouterr()
    cli_main(["memory", "status", "--config-path", str(cfg)])
    assert json.loads(capsys.readouterr().out)["registered"] is False


# -- live stdio transport (subprocess) -----------------------------------------------------

def test_mcp_server_over_stdio(tmp_path):
    db = str(tmp_path / "mcp.db")
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "memory_put_note", "arguments": {"task_id": "t", "key": "k", "value": "hello"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "memory_get_note", "arguments": {"task_id": "t", "key": "k"}}},
    ]
    stdin = "\n".join(json.dumps(r) for r in requests) + "\n"
    proc = subprocess.run(
        [sys.executable, "-m", "agentsuite.memory.mcp_server", "--db", db],
        input=stdin, capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT),
    )
    responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    by_id = {r["id"]: r for r in responses}
    assert by_id[1]["result"]["serverInfo"]["name"] == "agentsuite-memory"
    assert {t["name"] for t in by_id[2]["result"]["tools"]} >= {"memory_put_note", "memory_get_note"}
    # The note written in request 3 is read back in request 4 — proving shared, persisted memory.
    note_text = by_id[4]["result"]["content"][0]["text"]
    assert json.loads(note_text) == "hello"
