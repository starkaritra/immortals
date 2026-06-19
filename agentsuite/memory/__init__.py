"""Memory substrate (Phase 2, decisions AS-006/AS-007/AS-014).

A local-first SQLite store holding the append-only ``event/v1`` log (source of truth) plus
persisted artifacts (the blackboard), resolvable by id across runs. The orchestrator writes to
it through storage-agnostic callback sinks; a run is fully reconstructable by folding its event
log (:meth:`MemoryStore.reconstruct`). Derived read models (vector, graph) land in Phase 6;
MCP access in a later Phase 2 slice.
"""

from .store import (
    MemoryStore,
    ReplayResult,
    SCHEMA_VERSION,
    artifact_sink_for,
    event_sink_for,
)

__all__ = [
    "MemoryStore",
    "ReplayResult",
    "SCHEMA_VERSION",
    "artifact_sink_for",
    "event_sink_for",
]
