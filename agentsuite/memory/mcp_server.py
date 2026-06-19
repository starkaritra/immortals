#!/usr/bin/env python3
"""agentsuite memory MCP server — exposes the local SQLite store over MCP stdio (AS-021).

The orchestrator injects this into every worker (`--additional-mcp-config`) bound to the run's
``--db``, so agents share one audited memory: they can **read** the blackboard (artifacts) and the
event log, and **read/write** a free-form key/value scratchpad (``notes``). No third-party
dependencies — newline-delimited JSON-RPC 2.0 over stdin/stdout, mirroring the kgraph MCP server.

Run standalone (the orchestrator does this for you):
    python -m agentsuite.memory.mcp_server --db <path-to-store.db>
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from agentsuite.memory.store import MemoryStore

PROTOCOL_VERSION = "2024-11-05"

# name -> (description, input-property -> json-type, required-property-names)
TOOLS: list[tuple[str, str, dict[str, str], list[str]]] = [
    ("memory_get_artifact", "Fetch one persisted artifact by id for a task (the blackboard).",
     {"task_id": "string", "artifact_id": "string"}, ["task_id", "artifact_id"]),
    ("memory_list_artifacts", "List all persisted artifacts for a task (id -> artifact).",
     {"task_id": "string"}, ["task_id"]),
    ("memory_put_note", "Write a shared note (key/value scratchpad) for a task.",
     {"task_id": "string", "key": "string", "value": "string", "agent": "string"},
     ["task_id", "key", "value"]),
    ("memory_get_note", "Read a shared note's value by key for a task.",
     {"task_id": "string", "key": "string"}, ["task_id", "key"]),
    ("memory_list_notes", "List all shared notes for a task.",
     {"task_id": "string"}, ["task_id"]),
    ("memory_recent_events", "Read the recent event log for a task (newest last).",
     {"task_id": "string", "limit": "integer"}, ["task_id"]),
]
TOOL_NAMES = {t[0] for t in TOOLS}


def tool_schemas() -> list[dict[str, Any]]:
    out = []
    for name, desc, props, required in TOOLS:
        out.append({
            "name": name,
            "description": desc,
            "inputSchema": {
                "type": "object",
                "properties": {k: {"type": t} for k, t in props.items()},
                "required": required,
            },
        })
    return out


def call_tool(store: MemoryStore, name: str, arguments: dict[str, Any] | None) -> tuple[str, bool]:
    """Execute one tool against the store. Returns ``(json_text, is_error)``."""
    args = arguments or {}
    try:
        missing = [r for (n, _d, _p, req) in TOOLS if n == name for r in req if r not in args]
        if missing:
            return json.dumps({"error": f"missing required argument(s): {missing}"}), True

        if name == "memory_get_artifact":
            art = store.get_artifact(args["task_id"], args["artifact_id"])
            result: Any = art.to_dict() if art else None
        elif name == "memory_list_artifacts":
            result = {aid: a.to_dict() for aid, a in store.artifacts_for(args["task_id"]).items()}
        elif name == "memory_put_note":
            store.put_note(args["task_id"], args["key"], args["value"], args.get("agent"))
            result = {"ok": True, "key": args["key"]}
        elif name == "memory_get_note":
            result = store.get_note(args["task_id"], args["key"])
        elif name == "memory_list_notes":
            result = store.notes_for(args["task_id"])
        elif name == "memory_recent_events":
            events = store.events_for(args["task_id"])
            limit = args.get("limit")
            if isinstance(limit, int) and limit > 0:
                events = events[-limit:]
            result = events
        else:
            return json.dumps({"error": f"unknown tool: {name}"}), True
        return json.dumps(result, default=str), False
    except Exception as exc:  # noqa: BLE001 — surface any failure as an MCP tool error
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"}), True


def dispatch(store: MemoryStore, msg: dict[str, Any]) -> dict[str, Any] | None:
    """Map one JSON-RPC request to its response (or ``None`` for notifications)."""
    method = msg.get("method")
    mid = msg.get("id")
    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL_VERSION
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": ver,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "agentsuite-memory", "version": "1.0.0"},
        }}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": tool_schemas()}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name not in TOOL_NAMES:
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32602, "message": f"unknown tool: {name}"}}
        text, is_error = call_tool(store, name, params.get("arguments"))
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": text}], "isError": is_error}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method and method.startswith("notifications/"):
        return None
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"method not found: {method}"}}
    return None


def _resolve_db(argv: list[str]) -> str:
    """The store path: ``--db`` wins, else ``$AGENTSUITE_MEMORY_DB``, else a stable default.

    A default (rather than an error) keeps a *persistently-registered* server healthy in normal
    copilot sessions that don't set the env var; ``run --share-memory`` overrides it per run.
    """
    for i, tok in enumerate(argv):
        if tok == "--db" and i + 1 < len(argv):
            return argv[i + 1]
        if tok.startswith("--db="):
            return tok.split("=", 1)[1]
    env_db = os.environ.get("AGENTSUITE_MEMORY_DB")
    if env_db:
        return env_db
    default = os.path.join(os.path.expanduser("~"), ".copilot", "agentsuite", "memory.db")
    os.makedirs(os.path.dirname(default), exist_ok=True)
    return default


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    db_path = _resolve_db(argv)
    store = MemoryStore(db_path)
    out = sys.stdout
    try:
        out.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    log_path = os.environ.get("AGENTSUITE_MCP_LOG")

    def _log(text: str) -> None:
        if log_path:
            try:
                with open(log_path, "a", encoding="utf-8") as fh:
                    fh.write(text + "\n")
            except Exception:
                pass

    _log(f"-- server start, db={db_path} --")
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            _log(f"recv method={msg.get('method')} id={msg.get('id')}")
            response = dispatch(store, msg)
            if response is not None:
                payload = json.dumps(response)
                out.write(payload + "\n")
                out.flush()
                _log(f"sent {payload[:200]}")
    finally:
        store.close()


if __name__ == "__main__":
    main()
