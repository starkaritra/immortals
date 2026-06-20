"""Derived memory read-models: a knowledge graph + a semantic vector index (Phase 6, AS-023).

The append-only event log + artifacts + facts are the **source of truth**; this module *projects*
them into two derived, rebuildable read-models (CQRS — architecture §"Memory architecture"):

* **Knowledge graph** — nodes for tasks, agents, artifacts, and facts; edges ``produced_by``
  (artifact → agent), ``contains`` (task → artifact/fact), ``depends_on`` (artifact → artifact,
  from provenance inputs), and ``supersedes`` (fact → fact). Navigable for the manager.
* **Vector index** — a :class:`~agentsuite.memory.embedding.Embedder` vector per artifact and fact,
  enabling semantic ``search`` so the manager pulls only relevant prior context.

Both are *strictly a function of the source data*: :meth:`reindex` wipes and rebuilds them, so they
can never drift ahead of the log (a memory-poisoning guard, R5). Because the corpus is small they
are rebuilt on demand before a query; the seam leaves room for ``sqlite-vec`` + a real model later.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from agentsuite.memory.embedding import Embedder, cosine, default_embedder
from agentsuite.memory.store import MemoryStore

_DERIVED_SCHEMA = """
CREATE TABLE IF NOT EXISTS graph_nodes (
    key     TEXT PRIMARY KEY,
    kind    TEXT NOT NULL,
    label   TEXT,
    task_id TEXT
);
CREATE TABLE IF NOT EXISTS graph_edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    rel TEXT NOT NULL,
    PRIMARY KEY (src, dst, rel)
);
CREATE TABLE IF NOT EXISTS embeddings (
    ref_kind TEXT NOT NULL,          -- 'artifact' | 'fact'
    ref_task TEXT NOT NULL,
    ref_id   TEXT NOT NULL,
    agent    TEXT,
    text     TEXT NOT NULL,
    vector   TEXT NOT NULL,          -- JSON list[float]
    model    TEXT NOT NULL,
    PRIMARY KEY (ref_kind, ref_task, ref_id)
);
"""


@dataclass
class SearchHit:
    """One semantic-retrieval result."""

    kind: str          # 'artifact' | 'fact'
    task_id: str
    ref_id: str
    agent: str | None
    text: str
    score: float

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "task_id": self.task_id, "ref_id": self.ref_id,
            "agent": self.agent, "score": round(self.score, 6),
            "text": self.text[:500],
        }


def node_key(kind: str, ident: str) -> str:
    """Stable graph-node key, namespaced by kind (e.g. ``artifact:lesson``)."""
    return f"{kind}:{ident}"


def _artifact_text(artifact: dict) -> str:
    """A compact text rendering of an artifact for embedding (type + content)."""
    content = artifact.get("content")
    rendered = json.dumps(content, sort_keys=True, default=str) if content is not None else ""
    return f"{artifact.get('type', '')}: {rendered}".strip()


class DerivedMemory:
    """Graph + vector read-models projected from a :class:`MemoryStore`'s source data."""

    def __init__(self, store: MemoryStore, embedder: Embedder | None = None):
        self.store = store
        self.embedder = embedder or default_embedder()
        self._conn = store._conn  # same-package access to the shared connection
        self._conn.executescript(_DERIVED_SCHEMA)
        self._conn.commit()

    # -- projection ---------------------------------------------------------------------

    def reindex(self, task_id: str | None = None) -> None:
        """(Re)build the derived models from source. Scoped to ``task_id`` or the whole store.

        Idempotent and total for the chosen scope: existing derived rows for that scope are cleared
        first, so the read-models exactly reflect the current source of truth (no drift, R5).
        """
        tasks = [task_id] if task_id else self.store.tasks()
        if task_id is None:
            # tasks() folds the event log; artifacts or facts may exist for a task that has no
            # events (e.g. direct writes), so union every source table's task ids.
            extra = {
                r["task_id"] for r in self._conn.execute(
                    "SELECT task_id FROM artifacts UNION SELECT task_id FROM facts"
                ).fetchall()
            }
            tasks = sorted(set(tasks) | extra)

        for tid in tasks:
            self._clear_task(tid)
            self._project_task(tid)
        self._conn.commit()

    def _clear_task(self, task_id: str) -> None:
        self._conn.execute("DELETE FROM graph_nodes WHERE task_id = ?", (task_id,))
        self._conn.execute(
            "DELETE FROM graph_edges WHERE src LIKE ? OR dst LIKE ?",
            (f"%:{task_id}%", f"%:{task_id}%"),
        )
        self._conn.execute("DELETE FROM embeddings WHERE ref_task = ?", (task_id,))

    def _add_node(self, kind: str, ident: str, label: str | None, task_id: str | None) -> str:
        key = node_key(kind, ident)
        self._conn.execute(
            "INSERT OR REPLACE INTO graph_nodes (key, kind, label, task_id) VALUES (?, ?, ?, ?)",
            (key, kind, label, task_id),
        )
        return key

    def _add_edge(self, src: str, dst: str, rel: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO graph_edges (src, dst, rel) VALUES (?, ?, ?)", (src, dst, rel)
        )

    def _embed_ref(self, kind: str, task_id: str, ref_id: str, agent: str | None, text: str) -> None:
        vector = self.embedder.embed(text)
        self._conn.execute(
            "INSERT OR REPLACE INTO embeddings "
            "(ref_kind, ref_task, ref_id, agent, text, vector, model) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (kind, task_id, ref_id, agent, text, json.dumps(vector), self.embedder.name),
        )

    def _project_task(self, task_id: str) -> None:
        task_node = self._add_node("task", task_id, task_id, task_id)

        # Artifacts → nodes + produced_by/contains edges + embeddings.
        artifacts = self.store.artifacts_for(task_id)
        artifact_keys: set[str] = set()
        for aid, art in artifacts.items():
            d = art.to_dict()
            anode = self._add_node("artifact", f"{task_id}/{aid}", aid, task_id)
            artifact_keys.add(aid)
            self._add_edge(task_node, anode, "contains")
            if d.get("produced_by"):
                agent_node = self._add_node("agent", d["produced_by"], d["produced_by"], None)
                self._add_edge(anode, agent_node, "produced_by")
            text = _artifact_text(d)
            self._embed_ref("artifact", task_id, aid, d.get("produced_by"), text)

        # depends_on edges between artifacts, where provenance records upstream inputs.
        for aid, art in artifacts.items():
            anode = node_key("artifact", f"{task_id}/{aid}")
            for upstream in (art.provenance or {}).get("inputs", []) or []:
                if upstream in artifact_keys:
                    self._add_edge(anode, node_key("artifact", f"{task_id}/{upstream}"), "depends_on")

        # Facts → nodes + contains/supersedes edges + embeddings.
        for fact in self.store.facts_for(task_id):
            fid = fact["fact_id"]
            fnode = self._add_node("fact", fid, fact["text"][:80], task_id)
            self._add_edge(task_node, fnode, "contains")
            if fact.get("supersedes"):
                self._add_edge(fnode, node_key("fact", fact["supersedes"]), "supersedes")
            self._embed_ref("fact", task_id, fid, fact.get("agent"), fact["text"])

    # -- semantic retrieval -------------------------------------------------------------

    def search(self, query: str, *, task_id: str | None = None, agent: str | None = None,
               kinds: tuple[str, ...] = ("artifact", "fact"), top: int = 5,
               reindex: bool = True) -> list[SearchHit]:
        """Rank stored artifacts/facts by semantic similarity to ``query``.

        Optionally namespaced to a ``task_id`` and/or ``agent`` (the per-agent view). Rebuilds the
        index first by default so results reflect the latest source data.
        """
        if reindex:
            self.reindex(task_id)
        qvec = self.embedder.embed(query)

        clauses, params = ["ref_kind IN (%s)" % ",".join("?" * len(kinds))], list(kinds)
        if task_id is not None:
            clauses.append("ref_task = ?")
            params.append(task_id)
        if agent is not None:
            clauses.append("agent = ?")
            params.append(agent)
        rows = self._conn.execute(
            "SELECT ref_kind, ref_task, ref_id, agent, text, vector "
            f"FROM embeddings WHERE {' AND '.join(clauses)}", params
        ).fetchall()

        hits = [
            SearchHit(
                kind=r["ref_kind"], task_id=r["ref_task"], ref_id=r["ref_id"], agent=r["agent"],
                text=r["text"], score=cosine(qvec, json.loads(r["vector"])),
            )
            for r in rows
        ]
        hits = [h for h in hits if h.score > 0.0]
        hits.sort(key=lambda h: (-h.score, h.kind, h.ref_id))
        return hits[:top]

    # -- graph navigation ---------------------------------------------------------------

    def neighbors(self, key: str, *, direction: str = "both") -> list[dict]:
        """Edges incident to a node. ``direction`` ∈ {out, in, both}."""
        out: list[dict] = []
        if direction in ("out", "both"):
            for r in self._conn.execute(
                "SELECT src, dst, rel FROM graph_edges WHERE src = ? ORDER BY rel, dst", (key,)
            ).fetchall():
                out.append({"from": r["src"], "to": r["dst"], "rel": r["rel"], "dir": "out"})
        if direction in ("in", "both"):
            for r in self._conn.execute(
                "SELECT src, dst, rel FROM graph_edges WHERE dst = ? ORDER BY rel, src", (key,)
            ).fetchall():
                out.append({"from": r["src"], "to": r["dst"], "rel": r["rel"], "dir": "in"})
        return out

    def graph(self, task_id: str | None = None, *, reindex: bool = True) -> dict:
        """The knowledge graph (nodes + edges), optionally scoped to one task."""
        if reindex:
            self.reindex(task_id)
        if task_id is not None:
            node_rows = self._conn.execute(
                "SELECT key, kind, label, task_id FROM graph_nodes WHERE task_id = ? OR kind = 'agent' "
                "ORDER BY kind, key", (task_id,)
            ).fetchall()
            keys = {r["key"] for r in node_rows}
            edge_rows = [
                e for e in self._conn.execute(
                    "SELECT src, dst, rel FROM graph_edges ORDER BY rel, src, dst"
                ).fetchall() if e["src"] in keys and e["dst"] in keys
            ]
        else:
            node_rows = self._conn.execute(
                "SELECT key, kind, label, task_id FROM graph_nodes ORDER BY kind, key"
            ).fetchall()
            edge_rows = self._conn.execute(
                "SELECT src, dst, rel FROM graph_edges ORDER BY rel, src, dst"
            ).fetchall()
        return {
            "nodes": [dict(r) for r in node_rows],
            "edges": [{"from": r["src"], "to": r["dst"], "rel": r["rel"]} for r in edge_rows],
        }
