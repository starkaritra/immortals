"""Orchestrator-level guardrails (Phase 4, decision AS-005/AS-015).

Guardrails are *configurable caps the orchestrator enforces deterministically* — never
hard-coded thresholds. Every limit defaults to ``None`` (no cap): the owner opts in per run, so
the executor reports/halts only against limits explicitly set (coderAS "no hard-coded pass/fail
gates" principle). Enforcement lives in the orchestrator, not in individual agents (AS-005).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from agentsuite.contracts.models import Artifact, Node

# Returns True to approve a node's execution, False to deny.
ApprovalHandler = Callable[[Node], bool]


@dataclass(frozen=True)
class Guardrails:
    """Opt-in caps for a single run. ``None`` means *unlimited* for that dimension."""

    max_total_tokens: int | None = None       # cumulative tokens across the DAG
    max_wall_clock_s: float | None = None      # wall-clock budget for the whole run
    max_nodes: int | None = None               # max node executions (blunt budget guard)
    max_agent_invocations: int | None = None   # max calls to any single agent (loop guard)

    def is_active(self) -> bool:
        return any(
            v is not None
            for v in (
                self.max_total_tokens,
                self.max_wall_clock_s,
                self.max_nodes,
                self.max_agent_invocations,
            )
        )


class GuardrailBreach(Exception):
    """A guardrail was exceeded. ``reason`` is a stable, machine-readable token."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


def tokens_of(artifact: Artifact) -> int:
    """Best-effort token count from an artifact's provenance (``provenance.cost.total_tokens``).

    Returns 0 when the backend does not report usage, so the cap is a true ceiling that takes
    effect once usage reporting lands (no false trips on missing data).
    """
    cost = artifact.provenance.get("cost") if artifact.provenance else None
    if isinstance(cost, dict):
        val = cost.get("total_tokens")
        if isinstance(val, (int, float)):
            return int(val)
    return 0


@dataclass
class GuardrailState:
    """Mutable per-run tally checked against a :class:`Guardrails` config."""

    limits: Guardrails
    nodes_executed: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        self._agent_calls: dict[str, int] = {}

    def before_node(self, agent: str, elapsed_s: float) -> None:
        """Pre-invoke checks (run before spending on the next node)."""
        if self.limits.max_wall_clock_s is not None and elapsed_s > self.limits.max_wall_clock_s:
            raise GuardrailBreach(
                "wall_clock_exceeded",
                f"run exceeded wall-clock budget of {self.limits.max_wall_clock_s}s "
                f"({elapsed_s:.1f}s elapsed)",
            )
        if self.limits.max_nodes is not None and self.nodes_executed >= self.limits.max_nodes:
            raise GuardrailBreach(
                "max_nodes_exceeded",
                f"run reached node-execution cap of {self.limits.max_nodes}",
            )
        nxt = self._agent_calls.get(agent, 0) + 1
        if self.limits.max_agent_invocations is not None and nxt > self.limits.max_agent_invocations:
            raise GuardrailBreach(
                "agent_invocations_exceeded",
                f"agent {agent!r} would exceed its invocation cap of "
                f"{self.limits.max_agent_invocations}",
            )
        self._agent_calls[agent] = nxt
        self.nodes_executed += 1

    def after_node(self, artifact: Artifact) -> None:
        """Post-invoke accounting (after an artifact is produced)."""
        self.total_tokens += tokens_of(artifact)
        if self.limits.max_total_tokens is not None and self.total_tokens > self.limits.max_total_tokens:
            raise GuardrailBreach(
                "token_budget_exceeded",
                f"run exceeded token budget of {self.limits.max_total_tokens} "
                f"({self.total_tokens} used)",
            )
