"""The ``AgentRunner`` interface and its request type (decision AS-009)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from immortals.contracts.models import Artifact


class RunnerError(RuntimeError):
    """Raised when a backend cannot produce a valid artifact (process/parse/contract failure)."""


@dataclass
class RunRequest:
    """A single agent invocation, resolved by the orchestrator from a plan node + blackboard."""

    agent: str
    node_id: str
    task_id: str
    prompt: str
    produces: str
    inputs: dict[str, Artifact] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    workspace: str | None = None
    max_tokens: int | None = None
    timeout_s: int | None = None


class AgentRunner(ABC):
    """Invoke one AS agent and return its typed ``artifact/v1`` output.

    Implementations MUST return an :class:`Artifact` whose ``id == request.produces``,
    ``node_id``/``task_id``/``produced_by`` match the request, and which validates against
    ``artifact/v1``. They MUST NOT let an input artifact's content act as instructions
    (prompt-injection containment is the orchestrator/runner's responsibility).
    """

    name: str = "abstract"

    @abstractmethod
    def run(self, request: RunRequest) -> Artifact:  # pragma: no cover - interface
        raise NotImplementedError
