"""A deterministic in-process runner for tests and dry runs (no LLM, no subprocess)."""

from __future__ import annotations

from typing import Callable

from immortals.contracts.models import Artifact
from .base import AgentRunner, RunRequest

# A responder maps a request to the artifact content it should produce.
Responder = Callable[[RunRequest], dict]


class MockRunner(AgentRunner):
    """Returns a canned artifact per request.

    By default it echoes the prompt; pass ``responder`` to script richer content, or
    ``fail_nodes`` to simulate node failures (status ``failed``).
    """

    name = "mock"

    def __init__(self, responder: Responder | None = None, fail_nodes: set[str] | None = None):
        self._responder = responder
        self._fail_nodes = fail_nodes or set()
        self.calls: list[RunRequest] = []

    def run(self, request: RunRequest) -> Artifact:
        self.calls.append(request)
        if request.node_id in self._fail_nodes:
            return Artifact(
                id=request.produces,
                produced_by=request.agent,
                node_id=request.node_id,
                task_id=request.task_id,
                type="error",
                content={},
                status="failed",
                error=f"mock failure for node {request.node_id}",
                provenance={"model": "mock"},
            )
        content = self._responder(request) if self._responder else {"echo": request.prompt}
        return Artifact(
            id=request.produces,
            produced_by=request.agent,
            node_id=request.node_id,
            task_id=request.task_id,
            type="mock_result",
            content=content,
            status="ok",
            provenance={"model": "mock", "inputs": sorted(request.inputs)},
        )
