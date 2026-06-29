"""Read-only web inspector over an Immortals event store (prototype frontend).

A localhost FastAPI app + a single static page that renders four read-only views over an existing
``run --db`` SQLite store + derived memory: a runs list, a run detail (DAG + event timeline +
cost), an artifact viewer, and semantic recall + knowledge graph.

It deliberately adds **no** new core dependency — FastAPI/uvicorn live behind the ``[dashboard]``
optional extra (the core package stays ``jsonschema``-only). The GET endpoints here are the
read-half seed of the future Phase-8 manager-as-a-service API (AS-025): they reuse the existing
``MemoryStore`` / ``DerivedMemory`` read APIs verbatim and never write to the store except for the
derived index that ``DerivedMemory`` rebuilds on demand (as the ``recall`` CLI already does).

See ``design/prototype-frontend-handoff.md`` for the mandate and scope guards.
"""

from __future__ import annotations

__all__ = ["create_app"]


def create_app(db_path: str):
    """Lazily build the FastAPI app (keeps ``import immortals.dashboard`` dependency-free)."""
    from .app import create_app as _create_app

    return _create_app(db_path)
