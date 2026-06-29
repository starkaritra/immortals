"""Memory substrate (Phase 2, decisions AS-006/AS-007/AS-014; Phase 6 derived models AS-023).

A local-first SQLite store holding the append-only ``event/v1`` log (source of truth) plus
persisted artifacts (the blackboard) and agent-namespaced facts, resolvable by id across runs. The
orchestrator writes to it through storage-agnostic callback sinks; a run is fully reconstructable
by folding its event log (:meth:`MemoryStore.reconstruct`). Derived read-models — a knowledge graph
and a semantic vector index — are projected on demand by :class:`DerivedMemory` (Phase 6).
"""

from .derived import DerivedMemory, SearchHit
from .embedding import Embedder, HashingEmbedder, cosine, default_embedder
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
    "DerivedMemory",
    "SearchHit",
    "Embedder",
    "HashingEmbedder",
    "cosine",
    "default_embedder",
]
