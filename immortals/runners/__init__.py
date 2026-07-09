"""Swappable agent-invocation backends.

The ``AgentRunner`` interface decouples *what to run* (a plan node) from *how it's run*
(headless ``copilot`` today, LangGraph/ACP later). Every backend returns a validated
``artifact/v1``.
"""

from .base import AgentRunner, RunRequest, RunnerError
from .mock import MockRunner
from .copilot_backend import CopilotRunner
from .api_backend import ApiRunner
from .tools import ToolHarness

__all__ = [
    "AgentRunner", "RunRequest", "RunnerError",
    "MockRunner", "CopilotRunner", "ApiRunner", "ToolHarness",
]
