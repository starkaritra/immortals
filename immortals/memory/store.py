"""Local-first SQLite memory substrate (Phase 2, decisions AS-006/AS-007).

The append-only ``event/v1`` log is the source of truth; a run is a *fold* over its events.
Artifacts (the blackboard) are persisted alongside, resolvable by id across runs. The store is
deliberately storage-only and orchestrator-agnostic: the :class:`~immortals.orchestrator.Orchestrator`
writes to it through plain callback *sinks* (``event_sink``/``artifact_sink``), so nothing in the
execution path depends on SQLite (dependency inversion — AS-014).

Append-only is enforced in the database itself: triggers ``RAISE(ABORT)`` on any UPDATE/DELETE of
the ``events`` table, so the log cannot be silently rewritten even outside this API.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from immortals.contracts import validate
from immortals.contracts.models import Artifact


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


SCHEMA_VERSION = 3

# A free-form key/value scratchpad workers share through the MCP server (AS-021); the KV
# read-model of AS-006. Split out so it can also be applied as a v1 → v2 migration.
_NOTES_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    task_id TEXT NOT NULL,
    key     TEXT NOT NULL,
    agent   TEXT,
    value   TEXT NOT NULL,
    ts      TEXT,
    PRIMARY KEY (task_id, key)
);
"""

# Agent-namespaced facts: durable statements an agent asserts, each with provenance (``source``)
# and an optional ``supersedes`` pointer so stale facts can be retired rather than mutated
# (memory-poisoning mitigation, R5). Source data alongside artifacts — the derived knowledge graph
# and vector index in :mod:`immortals.memory.derived` index over both. Split out as a v2 → v3
# migration. (AS-023)
_FACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    fact_id    TEXT PRIMARY KEY,
    task_id    TEXT NOT NULL,
    agent      TEXT,
    text       TEXT NOT NULL,
    source     TEXT,
    supersedes TEXT,
    ts         TEXT
);
CREATE INDEX IF NOT EXISTS facts_task_idx ON facts(task_id);
CREATE INDEX IF NOT EXISTS facts_agent_idx ON facts(agent);
"""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id   TEXT NOT NULL UNIQUE,
    task_id    TEXT NOT NULL,
    ts         TEXT NOT NULL,
    type       TEXT NOT NULL,
    node_id    TEXT,
    agent      TEXT,
    payload    TEXT
);
CREATE INDEX IF NOT EXISTS events_task_idx ON events(task_id, seq);

CREATE TABLE IF NOT EXISTS artifacts (
    task_id     TEXT NOT NULL,
    id          TEXT NOT NULL,
    produced_by TEXT NOT NULL,
    node_id     TEXT NOT NULL,
    type        TEXT NOT NULL,
    content     TEXT NOT NULL,
    status      TEXT NOT NULL,
    provenance  TEXT,
    error       TEXT,
    untrusted   INTEGER NOT NULL DEFAULT 1,
    ts          TEXT,
    PRIMARY KEY (task_id, id)
);

-- Append-only enforcement: the event log is immutable (AS-006).
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events is append-only'); END;
""" + _NOTES_SCHEMA + _FACTS_SCHEMA


@dataclass
class ReplayResult:
    """A run reconstructed purely by folding its event log."""

    task_id: str
    status: str  # "completed" | "failed" | "running"
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    failed_node: str | None = None


class MemoryStore:
    """An event-sourced SQLite store: append-only events + persisted artifacts."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        # check_same_thread=False keeps the store usable from the orchestrator's call sites;
        # access is single-threaded today, bounded-parallel writers land in Phase 5.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        # The orchestrator and worker MCP servers may open the same file concurrently (WAL allows
        # one writer + many readers); wait rather than fail immediately on a held write lock.
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def _migrate(self) -> None:
        current = self._conn.execute("PRAGMA user_version").fetchone()[0]
        if current == 0:
            self._conn.executescript(_SCHEMA)
        elif current < SCHEMA_VERSION:
            # Incremental upgrades from older on-disk schemas.
            if current < 2:
                self._conn.executescript(_NOTES_SCHEMA)
            if current < 3:
                self._conn.executescript(_FACTS_SCHEMA)
        elif current > SCHEMA_VERSION:
            raise RuntimeError(
                f"store schema version {current} > supported {SCHEMA_VERSION}; upgrade immortals"
            )
        if current != SCHEMA_VERSION:
            self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._conn.commit()

    # -- context management -------------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- write sinks (the seams the orchestrator calls) ---------------------------------

    def append_event(self, event: dict) -> None:
        """Append one ``event/v1`` to the log. Idempotent on ``event_id`` (replay-safe)."""
        validate(event, "event/v1")
        payload = event.get("payload")
        self._conn.execute(
            "INSERT OR IGNORE INTO events (event_id, task_id, ts, type, node_id, agent, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event["event_id"],
                event["task_id"],
                event["ts"],
                event["type"],
                event.get("node_id"),
                event.get("agent"),
                json.dumps(payload) if payload is not None else None,
            ),
        )
        self._conn.commit()

    def put_artifact(self, artifact: Artifact) -> None:
        """Persist (upsert) an artifact, resolvable later by ``(task_id, id)``."""
        artifact.validate()
        d = artifact.to_dict()
        self._conn.execute(
            "INSERT INTO artifacts "
            "(task_id, id, produced_by, node_id, type, content, status, provenance, error, untrusted, ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(task_id, id) DO UPDATE SET "
            "produced_by=excluded.produced_by, node_id=excluded.node_id, type=excluded.type, "
            "content=excluded.content, status=excluded.status, provenance=excluded.provenance, "
            "error=excluded.error, untrusted=excluded.untrusted, ts=excluded.ts",
            (
                d["task_id"],
                d["id"],
                d["produced_by"],
                d["node_id"],
                d["type"],
                json.dumps(d["content"]),
                d["status"],
                json.dumps(d["provenance"]) if d.get("provenance") else None,
                d.get("error"),
                1 if d.get("untrusted", True) else 0,
                d.get("provenance", {}).get("ended"),
            ),
        )
        self._conn.commit()

    def put_note(self, task_id: str, key: str, value: object, agent: str | None = None) -> None:
        """Write a shared note (KV) for a task; the worker scratchpad behind the MCP server."""
        self._conn.execute(
            "INSERT INTO notes (task_id, key, agent, value, ts) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(task_id, key) DO UPDATE SET agent=excluded.agent, value=excluded.value, "
            "ts=excluded.ts",
            (task_id, key, agent, json.dumps(value), _utc_now()),
        )
        self._conn.commit()

    def get_note(self, task_id: str, key: str) -> object | None:
        row = self._conn.execute(
            "SELECT value FROM notes WHERE task_id = ? AND key = ?", (task_id, key)
        ).fetchone()
        return json.loads(row["value"]) if row else None

    def notes_for(self, task_id: str) -> dict[str, dict]:
        rows = self._conn.execute(
            "SELECT key, agent, value, ts FROM notes WHERE task_id = ? ORDER BY key", (task_id,)
        ).fetchall()
        return {
            r["key"]: {"value": json.loads(r["value"]), "agent": r["agent"], "ts": r["ts"]}
            for r in rows
        }

    def add_fact(self, task_id: str, text: str, agent: str | None = None,
                 source: str | None = None, fact_id: str | None = None,
                 supersedes: str | None = None) -> str:
        """Record an agent-namespaced fact with provenance; returns its ``fact_id``.

        ``supersedes`` retires an older fact (its id) without mutating it — the derived graph emits
        a ``supersedes`` edge so stale knowledge is traceable, not silently overwritten (R5).
        """
        fid = fact_id or hashlib.sha1(
            f"{task_id}|{agent}|{text}|{source}".encode("utf-8")
        ).hexdigest()[:16]
        self._conn.execute(
            "INSERT INTO facts (fact_id, task_id, agent, text, source, supersedes, ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(fact_id) DO UPDATE SET text=excluded.text, agent=excluded.agent, "
            "source=excluded.source, supersedes=excluded.supersedes, ts=excluded.ts",
            (fid, task_id, agent, text, source, supersedes, _utc_now()),
        )
        self._conn.commit()
        return fid

    def facts_for(self, task_id: str | None = None, agent: str | None = None) -> list[dict]:
        """Facts, optionally namespaced by ``task_id`` and/or ``agent`` (the per-agent view)."""
        clauses, params = [], []
        if task_id is not None:
            clauses.append("task_id = ?")
            params.append(task_id)
        if agent is not None:
            clauses.append("agent = ?")
            params.append(agent)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self._conn.execute(
            "SELECT fact_id, task_id, agent, text, source, supersedes, ts "
            f"FROM facts{where} ORDER BY ts", params
        ).fetchall()
        return [dict(r) for r in rows]

    # -- read models --------------------------------------------------------------------

    def events_for(self, task_id: str) -> list[dict]:
        """All events for a task, in append (``seq``) order."""
        rows = self._conn.execute(
            "SELECT event_id, task_id, ts, type, node_id, agent, payload "
            "FROM events WHERE task_id = ? ORDER BY seq",
            (task_id,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_artifact(self, task_id: str, artifact_id: str) -> Artifact | None:
        row = self._conn.execute(
            "SELECT * FROM artifacts WHERE task_id = ? AND id = ?", (task_id, artifact_id)
        ).fetchone()
        return self._row_to_artifact(row) if row else None

    def artifacts_for(self, task_id: str) -> dict[str, Artifact]:
        rows = self._conn.execute(
            "SELECT * FROM artifacts WHERE task_id = ?", (task_id,)
        ).fetchall()
        return {r["id"]: self._row_to_artifact(r) for r in rows}

    def tasks(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT task_id FROM events ORDER BY task_id"
        ).fetchall()
        return [r["task_id"] for r in rows]

    def reconstruct(self, task_id: str) -> ReplayResult:
        """Fold the event log into a run state — the source-of-truth reconstruction."""
        events = self.events_for(task_id)
        if not events:
            raise KeyError(f"no events for task {task_id!r}")
        status = "running"
        failed_node: str | None = None
        for ev in events:
            if ev["type"] == "run_completed":
                status = "completed"
            elif ev["type"] == "node_failed":
                status = "failed"
                failed_node = ev.get("node_id") or failed_node
        return ReplayResult(
            task_id=task_id,
            status=status,
            artifacts=self.artifacts_for(task_id),
            events=events,
            failed_node=failed_node,
        )

    # -- row mappers --------------------------------------------------------------------

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> dict:
        ev: dict = {
            "schema": "event/v1",
            "event_id": row["event_id"],
            "task_id": row["task_id"],
            "ts": row["ts"],
            "type": row["type"],
        }
        if row["node_id"] is not None:
            ev["node_id"] = row["node_id"]
        if row["agent"] is not None:
            ev["agent"] = row["agent"]
        if row["payload"] is not None:
            ev["payload"] = json.loads(row["payload"])
        return ev

    @staticmethod
    def _row_to_artifact(row: sqlite3.Row) -> Artifact:
        return Artifact(
            id=row["id"],
            produced_by=row["produced_by"],
            node_id=row["node_id"],
            task_id=row["task_id"],
            type=row["type"],
            content=json.loads(row["content"]),
            status=row["status"],
            provenance=json.loads(row["provenance"]) if row["provenance"] else {},
            error=row["error"],
            untrusted=bool(row["untrusted"]),
        )


def event_sink_for(store: MemoryStore) -> Callable[[dict], None]:
    """Convenience: the ``event_sink`` callable the orchestrator expects."""
    return store.append_event


def artifact_sink_for(store: MemoryStore) -> Callable[[Artifact], None]:
    """Convenience: the ``artifact_sink`` callable the orchestrator expects."""
    return store.put_artifact
