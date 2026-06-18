"""Ergonomic dataclasses over the JSON contracts.

These are thin conveniences for orchestrator code; the JSON Schemas in ``schemas/`` remain
the source of truth. ``to_dict``/``from_dict`` round-trip to the wire format, and
``Plan.validate`` / ``Artifact.validate`` defer to :mod:`agentsuite.contracts.validate`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from .validate import validate as _validate_contract


def _prune(d: dict[str, Any]) -> dict[str, Any]:
    """Drop keys whose value is None or an empty list/dict so the wire form stays minimal."""
    out: dict[str, Any] = {}
    for k, val in d.items():
        if val is None or val == [] or val == {}:
            continue
        out[k] = val
    return out


@dataclass
class Node:
    id: str
    agent: str
    prompt: str
    produces: str
    inputs: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    context_refs: list[str] = field(default_factory=list)
    success_criteria: str | None = None
    reversibility: str = "reversible"
    approval: str = "none"
    budget: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _prune(asdict(self))


@dataclass
class Edge:
    from_: str
    to: str
    on: str = "success"

    def to_dict(self) -> dict[str, Any]:
        return {"from": self.from_, "to": self.to, "on": self.on}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Edge":
        return cls(from_=d["from"], to=d["to"], on=d.get("on", "success"))


@dataclass
class Plan:
    task_id: str
    goal: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    objective: str | None = None
    key_results: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "schema": "plan/v1",
            "task_id": self.task_id,
            "goal": self.goal,
            "nodes": [n.to_dict() for n in self.nodes],
        }
        if self.objective:
            d["objective"] = self.objective
        if self.key_results:
            d["key_results"] = self.key_results
        if self.edges:
            d["edges"] = [e.to_dict() for e in self.edges]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Plan":
        _validate_contract(d, "plan/v1")
        nodes = [
            Node(
                id=n["id"],
                agent=n["agent"],
                prompt=n["prompt"],
                produces=n["produces"],
                inputs=n.get("inputs", []),
                depends_on=n.get("depends_on", []),
                context_refs=n.get("context_refs", []),
                success_criteria=n.get("success_criteria"),
                reversibility=n.get("reversibility", "reversible"),
                approval=n.get("approval", "none"),
                budget=n.get("budget", {}),
            )
            for n in d["nodes"]
        ]
        edges = [Edge.from_dict(e) for e in d.get("edges", [])]
        return cls(
            task_id=d["task_id"],
            goal=d["goal"],
            nodes=nodes,
            edges=edges,
            objective=d.get("objective"),
            key_results=d.get("key_results", []),
        )

    def validate(self) -> None:
        _validate_contract(self.to_dict(), "plan/v1")

    def node(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(f"no node {node_id!r} in plan {self.task_id!r}")


@dataclass
class Artifact:
    id: str
    produced_by: str
    node_id: str
    task_id: str
    type: str
    content: dict[str, Any]
    status: str = "ok"
    provenance: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    untrusted: bool = True

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "schema": "artifact/v1",
            "id": self.id,
            "produced_by": self.produced_by,
            "node_id": self.node_id,
            "task_id": self.task_id,
            "type": self.type,
            "content": self.content,
            "status": self.status,
            "untrusted": self.untrusted,
        }
        if self.provenance:
            d["provenance"] = self.provenance
        if self.error:
            d["error"] = self.error
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Artifact":
        _validate_contract(d, "artifact/v1")
        return cls(
            id=d["id"],
            produced_by=d["produced_by"],
            node_id=d["node_id"],
            task_id=d["task_id"],
            type=d["type"],
            content=d["content"],
            status=d.get("status", "ok"),
            provenance=d.get("provenance", {}),
            error=d.get("error"),
            untrusted=d.get("untrusted", True),
        )

    def validate(self) -> None:
        _validate_contract(self.to_dict(), "artifact/v1")
