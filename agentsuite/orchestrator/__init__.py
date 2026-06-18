"""Deterministic DAG orchestrator (the mechanism, decisions AS-001/002/008).

Validates a ``plan/v1`` against the schema *and* the capability registry, topologically
orders the nodes, executes each through an :class:`AgentRunner`, validates every returned
artifact against ``artifact/v1`` (the seam contract), routes typed artifacts via an in-memory
blackboard, and emits an event trail. Parallelism, resume, and the SQLite event log come in
later phases; the control flow here is fully deterministic.
"""

from .runner import Orchestrator, RunResult

__all__ = ["Orchestrator", "RunResult"]
