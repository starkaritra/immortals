"""Memory substrate (Phase 2).

Planned: a local-first SQLite store holding the append-only ``event/v1`` log (source of
truth) plus derived read models (graph, vector, KV), exposed over MCP (decisions AS-006/007).
Not yet implemented — the orchestrator currently keeps the blackboard and event trail in
memory and returns them in :class:`agentsuite.orchestrator.RunResult`.
"""
