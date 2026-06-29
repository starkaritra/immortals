"""Tests for Phase 6 derived memory: facts, embedder, graph projection, semantic search (AS-023)."""

from __future__ import annotations

import json

import pytest

from immortals.cli import main
from immortals.contracts.models import Artifact
from immortals.memory import DerivedMemory, HashingEmbedder, MemoryStore, cosine, default_embedder
from immortals.memory import mcp_server as srv


@pytest.fixture
def store():
    s = MemoryStore(":memory:")
    yield s
    s.close()


def _artifact(task_id: str, art_id: str, type_: str, content: dict,
              produced_by: str = "teachAS", inputs: list[str] | None = None) -> Artifact:
    return Artifact(
        id=art_id, produced_by=produced_by, node_id=f"n-{art_id}", task_id=task_id,
        type=type_, content=content,
        provenance={"model": "mock", "inputs": inputs or []},
    )


# -- embedder ------------------------------------------------------------------------------

def test_embedder_is_deterministic():
    e = HashingEmbedder(dim=64)
    assert e.embed("eigenvectors and eigenvalues") == e.embed("eigenvectors and eigenvalues")


def test_embedder_unit_norm_and_dim():
    e = HashingEmbedder(dim=128)
    v = e.embed("a quick brown fox")
    assert len(v) == 128
    assert cosine(v, v) == pytest.approx(1.0)


def test_embedder_similar_text_scores_higher():
    e = default_embedder()
    q = e.embed("how do neural networks learn")
    near = e.embed("neural networks learn by gradient descent")
    far = e.embed("the history of roman aqueducts")
    assert cosine(q, near) > cosine(q, far)


def test_empty_text_embeds_to_zero_vector():
    e = HashingEmbedder(dim=16)
    assert cosine(e.embed(""), e.embed("anything")) == 0.0


# -- facts (source) ------------------------------------------------------------------------

def test_facts_roundtrip_and_namespacing(store):
    store.add_fact("t1", "caching speeds repeated lookups", agent="coderAS", source="commit:abc")
    store.add_fact("t1", "eviction is irreversible", agent="discussAS", source="doc:x")
    store.add_fact("t2", "other task fact", agent="coderAS")

    assert len(store.facts_for("t1")) == 2
    coder = store.facts_for("t1", agent="coderAS")
    assert len(coder) == 1 and coder[0]["source"] == "commit:abc"
    assert len(store.facts_for(agent="coderAS")) == 2  # across tasks


def test_fact_id_stable_and_upsert(store):
    fid1 = store.add_fact("t", "same text", agent="a", source="s")
    fid2 = store.add_fact("t", "same text", agent="a", source="s")
    assert fid1 == fid2
    assert len(store.facts_for("t")) == 1


def test_fact_supersedes_recorded(store):
    old = store.add_fact("t", "old claim", agent="a")
    new = store.add_fact("t", "corrected claim", agent="a", supersedes=old)
    facts = {f["fact_id"]: f for f in store.facts_for("t")}
    assert facts[new]["supersedes"] == old


# -- schema migration v2 -> v3 -------------------------------------------------------------

def test_v2_store_migrates_to_v3(tmp_path):
    import sqlite3

    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA user_version = 2")
    conn.execute("CREATE TABLE events (seq INTEGER PRIMARY KEY, event_id TEXT, task_id TEXT, "
                 "ts TEXT, type TEXT, node_id TEXT, agent TEXT, payload TEXT)")
    conn.commit()
    conn.close()

    s = MemoryStore(str(db))
    try:
        s.add_fact("t", "a fact after migration", agent="x")
        assert s.facts_for("t")[0]["text"] == "a fact after migration"
    finally:
        s.close()


# -- derived graph -------------------------------------------------------------------------

def test_graph_projects_nodes_and_edges(store):
    store.put_artifact(_artifact("t", "lesson", "lesson", {"text": "what eigenvectors are"}))
    store.put_artifact(_artifact("t", "quiz", "quiz", {"q": "compute eigenvalues"},
                                 inputs=["lesson"]))
    store.add_fact("t", "eigenvectors keep direction under a transform", agent="teachAS")

    d = DerivedMemory(store)
    g = d.graph("t")
    kinds = {n["key"]: n["kind"] for n in g["nodes"]}
    assert "task:t" in kinds and kinds["artifact:t/lesson"] == "artifact"
    assert any(n["kind"] == "agent" and n["key"] == "agent:teachAS" for n in g["nodes"])

    rels = {(e["from"], e["to"], e["rel"]) for e in g["edges"]}
    assert ("artifact:t/lesson", "agent:teachAS", "produced_by") in rels
    assert ("task:t", "artifact:t/quiz", "contains") in rels
    assert ("artifact:t/quiz", "artifact:t/lesson", "depends_on") in rels


def test_graph_supersedes_edge(store):
    old = store.add_fact("t", "old", agent="a")
    store.add_fact("t", "new", agent="a", supersedes=old)
    g = DerivedMemory(store).graph("t")
    assert any(e["rel"] == "supersedes" for e in g["edges"])


def test_neighbors_navigation(store):
    store.put_artifact(_artifact("t", "lesson", "lesson", {"text": "hello"}))
    d = DerivedMemory(store)
    d.reindex("t")
    out = d.neighbors("artifact:t/lesson", direction="out")
    assert any(e["to"] == "agent:teachAS" and e["rel"] == "produced_by" for e in out)


# -- semantic search -----------------------------------------------------------------------

def test_search_ranks_relevant_artifact_first(store):
    store.put_artifact(_artifact("t", "eig", "lesson",
                                 {"text": "eigenvectors and eigenvalues of a matrix"}))
    store.put_artifact(_artifact("t", "rome", "lesson",
                                 {"text": "the roman aqueducts carried water"}))
    d = DerivedMemory(store)
    hits = d.search("explain eigenvalues of a matrix", task_id="t")
    assert hits and hits[0].ref_id == "eig"


def test_search_indexes_facts_and_artifacts(store):
    store.put_artifact(_artifact("t", "a1", "note", {"text": "budget discipline matters"}))
    store.add_fact("t", "always cache expensive llm calls", agent="coderAS")
    d = DerivedMemory(store)
    hits = d.search("caching llm calls", task_id="t")
    assert hits and hits[0].kind == "fact"


def test_search_agent_namespace_scoping(store):
    store.add_fact("t", "shared concept about gradients", agent="teachAS")
    store.add_fact("t", "shared concept about gradients", agent="coderAS", fact_id="other")
    d = DerivedMemory(store)
    hits = d.search("gradients", task_id="t", agent="teachAS")
    assert hits and all(h.agent == "teachAS" for h in hits)


def test_search_reindex_reflects_new_data(store):
    d = DerivedMemory(store)
    assert d.search("anything", task_id="t") == []
    store.add_fact("t", "freshly added knowledge", agent="a")
    hits = d.search("freshly added knowledge", task_id="t")
    assert hits and hits[0].kind == "fact"


def test_search_single_shared_token_in_long_doc(store):
    """Regression: a genuine single-token match in a longer doc must rank, never cancel to zero
    (unsigned hashed bag-of-words; signed hashing silently zeroed this — AS-023)."""
    store.put_artifact(_artifact(
        "t", "lesson", "lesson",
        {"echo": "Teach the user what eigenvectors and eigenvalues are, from the ground up, "
                 "intuition before formula, with a worked 2x2 example."}))
    d = DerivedMemory(store)
    hits = d.search("explain eigenvalues", task_id="t")
    assert hits and hits[0].ref_id == "lesson" and hits[0].score > 0.0


# -- MCP surface ---------------------------------------------------------------------------

def _call(store, name, args):
    text, is_error = srv.call_tool(store, name, args)
    return json.loads(text), is_error


def test_mcp_add_and_list_facts(store):
    res, err = _call(store, "memory_add_fact",
                     {"task_id": "t", "text": "a durable fact", "agent": "coderAS",
                      "source": "doc:y"})
    assert not err and res["ok"]
    listed, err = _call(store, "memory_list_facts", {"task_id": "t"})
    assert not err and listed[0]["text"] == "a durable fact"


def test_mcp_search_and_graph(store):
    store.put_artifact(_artifact("t", "eig", "lesson", {"text": "eigenvalues of a matrix"}))
    hits, err = _call(store, "memory_search", {"query": "eigenvalues", "task_id": "t"})
    assert not err and hits and hits[0]["ref_id"] == "eig"

    graph, err = _call(store, "memory_graph", {"task_id": "t"})
    assert not err and any(n["key"] == "artifact:t/eig" for n in graph["nodes"])


def test_mcp_search_listed_in_tool_schemas():
    names = {t["name"] for t in srv.tool_schemas()}
    assert {"memory_search", "memory_graph", "memory_add_fact", "memory_list_facts"} <= names


# -- CLI recall ----------------------------------------------------------------------------

def test_cli_recall_search(tmp_path, capsys):
    db = str(tmp_path / "r.db")
    s = MemoryStore(db)
    s.put_artifact(_artifact("t", "eig", "lesson", {"text": "eigenvalues of a matrix"}))
    s.add_fact("t", "roman aqueducts carried water", agent="teachAS")
    s.close()

    rc = main(["recall", "--db", db, "--query", "eigenvalues", "--task-id", "t"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["hits"][0]["ref_id"] == "eig"


def test_cli_recall_graph(tmp_path, capsys):
    db = str(tmp_path / "g.db")
    s = MemoryStore(db)
    s.put_artifact(_artifact("t", "eig", "lesson", {"text": "x"}))
    s.close()

    rc = main(["recall", "--db", db, "--graph", "--task-id", "t"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and any(n["key"] == "task:t" for n in out["nodes"])
