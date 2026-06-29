"""FastAPI app factory for the read-only dashboard.

Every endpoint opens a fresh :class:`~immortals.memory.MemoryStore` for the request and closes it
after (the store is cheap and ``check_same_thread=False`` + WAL makes concurrent readers safe), so
there is no shared mutable connection state across requests. All routes are ``GET`` and read-only;
they mirror the JSON shapes the ``replay`` / ``recall`` CLI commands already emit so the dashboard
and the CLI stay consistent — and so these routes can become the Phase-8 read API unchanged.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from immortals.memory import DerivedMemory, MemoryStore, ReplayResult

_STATIC_DIR = Path(__file__).resolve().parent / "static"


# -- shaping helpers (kept framework-free so they're unit-testable without a server) -------------

def _total_tokens(result: ReplayResult) -> int:
    """Sum ``provenance.cost.total_tokens`` across a run's artifacts (0 when unreported)."""
    total = 0
    for art in result.artifacts.values():
        cost = (art.provenance or {}).get("cost") or {}
        total += cost.get("total_tokens") or 0
    return total


def run_summary(store: MemoryStore, task_id: str) -> dict[str, Any]:
    """One row for the runs list: status, node/artifact counts, total tokens, last-event ts."""
    result = store.reconstruct(task_id)
    node_ids = {e["node_id"] for e in result.events if e.get("node_id")}
    return {
        "task_id": task_id,
        "status": result.status,
        "node_count": len(node_ids),
        "artifact_count": len(result.artifacts),
        "event_count": len(result.events),
        "total_tokens": _total_tokens(result),
        "last_event_ts": result.events[-1]["ts"] if result.events else None,
        "failed_node": result.failed_node,
    }


def replay_dict(result: ReplayResult) -> dict[str, Any]:
    """The run-detail shape — mirrors ``cli._replay_to_dict(result, include_events=True)``."""
    out: dict[str, Any] = {
        "task_id": result.task_id,
        "status": result.status,
        "artifacts": {aid: art.to_dict() for aid, art in result.artifacts.items()},
        "events": result.events,
    }
    if result.failed_node:
        out["failed_node"] = result.failed_node
    return out


def create_app(db_path: str):
    """Build the FastAPI app bound to one event store at ``db_path``.

    Raises a clear ``ModuleNotFoundError`` (with the install hint) if the ``[dashboard]`` extra is
    missing, rather than failing obscurely deep in an import.
    """
    try:
        from fastapi import FastAPI, HTTPException, Query
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised via the CLI guard
        raise ModuleNotFoundError(
            "The Immortals dashboard needs the optional extra. "
            'Install it with:  pip install -e ".[dashboard]"'
        ) from exc

    app = FastAPI(title="Immortals dashboard", version="0.1.0",
                  summary="Read-only inspector over an Immortals run store.")

    @contextmanager
    def _store() -> Iterator[MemoryStore]:
        store = MemoryStore(db_path)
        try:
            yield store
        finally:
            store.close()

    @app.get("/api/runs")
    def list_runs() -> dict[str, Any]:
        """All runs in the store, summarized (the runs-list view)."""
        with _store() as store:
            return {"db": db_path, "tasks": [run_summary(store, t) for t in store.tasks()]}

    @app.get("/api/runs/{task_id}")
    def run_detail(task_id: str) -> dict[str, Any]:
        """A reconstructed run: status, artifacts, full event timeline (the run-detail view)."""
        with _store() as store:
            try:
                result = store.reconstruct(task_id)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"no such task {task_id!r}")
            return replay_dict(result)

    @app.get("/api/runs/{task_id}/graph")
    def run_graph(task_id: str) -> dict[str, Any]:
        """The DAG / knowledge graph for one run (nodes + produced_by/contains/depends_on edges)."""
        with _store() as store:
            return DerivedMemory(store).graph(task_id)

    @app.get("/api/artifacts/{task_id}/{artifact_id}")
    def artifact(task_id: str, artifact_id: str) -> dict[str, Any]:
        """One artifact's content + provenance (the artifact-viewer view)."""
        with _store() as store:
            art = store.get_artifact(task_id, artifact_id)
            if art is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"no artifact {artifact_id!r} in task {task_id!r}",
                )
            return art.to_dict()

    @app.get("/api/recall")
    def recall(
        q: str = Query(..., min_length=1, description="Free-text semantic query."),
        task_id: str | None = None,
        agent: str | None = None,
        top: int = Query(5, ge=1, le=50),
    ) -> dict[str, Any]:
        """Rank stored artifacts/facts by semantic relevance (the recall view)."""
        with _store() as store:
            hits = DerivedMemory(store).search(q, task_id=task_id, agent=agent, top=top)
            return {"query": q, "hits": [h.to_dict() for h in hits]}

    @app.get("/api/graph")
    def graph(task_id: str | None = None) -> dict[str, Any]:
        """The whole-store knowledge graph (or one task's, if ``task_id`` is given)."""
        with _store() as store:
            return DerivedMemory(store).graph(task_id)

    @app.get("/", include_in_schema=False)
    def index() -> Any:
        return FileResponse(_STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    return app
