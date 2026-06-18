"""Load and query agent capability manifests (``registry/v1``).

managerAS routes by matching a task's needs to these manifests; the orchestrator uses the
registry to type-check a plan (every node's ``agent`` must be registered).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentsuite.contracts import validate

# Default location: the repo-root ``registry/`` directory (sibling of the ``agentsuite``
# package), holding one ``<agent>.json`` manifest per worker agent.
DEFAULT_REGISTRY_DIR = Path(__file__).resolve().parents[2] / "registry"


@dataclass(frozen=True)
class AgentManifest:
    agent: str
    summary: str
    capabilities: tuple[str, ...]
    consumes: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    approval_default: str = "none"
    cost_hint: str = "medium"
    when_to_use: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AgentManifest":
        validate(d, "registry/v1")
        return cls(
            agent=d["agent"],
            summary=d["summary"],
            capabilities=tuple(d["capabilities"]),
            consumes=tuple(d.get("consumes", [])),
            produces=tuple(d.get("produces", [])),
            approval_default=d.get("approval_default", "none"),
            cost_hint=d.get("cost_hint", "medium"),
            when_to_use=d.get("when_to_use", ""),
        )


@dataclass
class Registry:
    manifests: dict[str, AgentManifest] = field(default_factory=dict)

    @classmethod
    def load(cls, directory: Path | str | None = None) -> "Registry":
        path = Path(directory) if directory is not None else DEFAULT_REGISTRY_DIR
        if not path.is_dir():
            raise FileNotFoundError(f"registry directory not found: {path}")
        manifests: dict[str, AgentManifest] = {}
        for f in sorted(path.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            manifest = AgentManifest.from_dict(data)
            manifests[manifest.agent] = manifest
        return cls(manifests=manifests)

    def __contains__(self, agent: str) -> bool:
        return agent in self.manifests

    def get(self, agent: str) -> AgentManifest:
        try:
            return self.manifests[agent]
        except KeyError:
            raise KeyError(f"agent {agent!r} is not registered; known: {sorted(self.manifests)}")

    def agents(self) -> list[str]:
        return sorted(self.manifests)

    def with_capability(self, capability: str) -> list[AgentManifest]:
        """All agents advertising ``capability`` (used by managerAS for routing)."""
        return [m for m in self.manifests.values() if capability in m.capabilities]
