"""Load and query agent capability manifests (``registry/v1``).

managerAS routes by matching a task's needs to these manifests; the orchestrator uses the
registry to type-check a plan (every node's ``agent`` must be registered) and, optionally, to
apply each agent's ``approval_default`` as a sign-off floor.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentsuite.contracts import validate
from agentsuite import config

# Default location resolves through :mod:`agentsuite.config` (env-overridable), holding one
# ``<agent>.json`` manifest per worker agent.
def _default_registry_dir() -> Path:
    return config.registry_dir()

# Tiny stopword set so free-text routing matches on meaningful tokens only.
_STOPWORDS = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "are", "was", "out", "can", "will", "use", "used", "using", "about", "what",
    "how", "why", "when", "who", "a", "an", "to", "of", "in", "on", "or", "is",
    "it", "as", "by", "be", "do", "my", "me", "i",
})


def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 2 and t not in _STOPWORDS}


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "summary": self.summary,
            "capabilities": list(self.capabilities),
            "consumes": list(self.consumes),
            "produces": list(self.produces),
            "approval_default": self.approval_default,
            "cost_hint": self.cost_hint,
            "when_to_use": self.when_to_use,
        }


@dataclass
class Registry:
    manifests: dict[str, AgentManifest] = field(default_factory=dict)

    @classmethod
    def load(cls, directory: Path | str | None = None) -> "Registry":
        path = Path(directory) if directory is not None else _default_registry_dir()
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

    def describe(self) -> list[dict[str, Any]]:
        """All manifests as plain dicts, agent-sorted — the catalogue managerAS reads to route."""
        return [self.manifests[a].to_dict() for a in self.agents()]

    def with_capability(self, capability: str) -> list[AgentManifest]:
        """All agents advertising ``capability`` (exact match)."""
        return [m for m in self.manifests.values() if capability in m.capabilities]

    def route(self, need: str, top: int | None = None) -> list[dict[str, Any]]:
        """Rank agents against a free-text or capability ``need`` (deterministic, no LLM).

        Scores each manifest by: exact/normalised capability phrase hits (heavy), capability-token
        overlap (medium), and overlap with ``when_to_use``/``summary`` (light). Returns
        ``[{agent, score, reasons, capabilities, when_to_use}, …]`` sorted by score desc then name.
        """
        need_lc = need.lower()
        need_tokens = _tokenize(need)
        ranked: list[dict[str, Any]] = []
        for agent in self.agents():
            m = self.manifests[agent]
            score = 0
            reasons: list[str] = []
            for cap in m.capabilities:
                phrase = cap.replace("_", " ")
                if cap in need_lc or phrase in need_lc:
                    score += 5
                    reasons.append(f"capability:{cap}")
            cap_tokens = _tokenize(" ".join(m.capabilities))
            cap_overlap = need_tokens & cap_tokens
            score += 2 * len(cap_overlap)
            reasons += sorted(f"cap~{t}" for t in cap_overlap)
            text_overlap = need_tokens & _tokenize(m.when_to_use + " " + m.summary)
            score += len(text_overlap)
            reasons += sorted(f"text~{t}" for t in text_overlap)
            if score > 0:
                ranked.append({
                    "agent": agent,
                    "score": score,
                    "reasons": reasons,
                    "capabilities": list(m.capabilities),
                    "when_to_use": m.when_to_use,
                    "cost_hint": m.cost_hint,
                    "approval_default": m.approval_default,
                })
        ranked.sort(key=lambda r: (-r["score"], r["agent"]))
        return ranked[:top] if top else ranked
