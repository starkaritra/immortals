"""Goal → plan/v1 planning for the orchestration UI (AS-033).

Two planners turn a plain-English goal into a runnable DAG:

- ``plan_via_route`` — **deterministic, no LLM/key**: uses the registry's routing to pick the most
  relevant agents and chains them into a small pipeline. Lets the orchestration DAG be demoed (and
  tested) with the ``mock`` worker backend, no API key required.
- ``plan_via_manager`` — the real **managerAS** planner: prompts the manager persona (via a model
  provider) to emit a ``plan/v1`` JSON for the goal, then parses + validates it.

Both return a validated :class:`~immortals.contracts.models.Plan`.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from immortals import config
from immortals.contracts.models import Node, Plan
from immortals.registry import Registry
from immortals.runners.providers import ChatMessage, ModelProvider

_FRONTMATTER = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "goal"


def plan_via_route(goal: str, registry: Registry | None = None, top: int = 3) -> Plan:
    """A deterministic pipeline of the top-routed agents for ``goal`` (no LLM)."""
    registry = registry or Registry.load()
    ranked = [r for r in registry.route(goal, top=top) if r.get("score", 0) > 0]
    if not ranked:
        ranked = registry.route(goal, top=1)  # always produce at least one node

    task_id = f"orchestrate-{_slug(goal)[:24]}-{uuid.uuid4().hex[:6]}"
    nodes: list[Node] = []
    prev: str | None = None
    for i, r in enumerate(ranked):
        nid = f"n{i + 1}"
        produces = f"{nid}-out"
        prompt = goal if i == 0 else (
            f"Continue toward the overall goal using the prior step's result.\nGoal: {goal}"
        )
        nodes.append(Node(
            id=nid, agent=r["agent"], prompt=prompt, produces=produces,
            inputs=[prev] if prev else [], depends_on=[f"n{i}"] if i > 0 else [],
        ))
        prev = produces
    plan = Plan(task_id=task_id, goal=goal, nodes=nodes)
    plan.validate()
    return plan


def _persona(agent: str) -> str:
    path = config.agents_dir() / f"{agent}.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    return _FRONTMATTER.sub("", text, count=1).strip()


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first balanced ``{...}`` JSON object out of a model response."""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        start = text.find("{")
        if start < 0:
            raise ValueError("no JSON object found in planner output")
        depth = 0
        for i in range(start, len(text)):
            depth += 1 if text[i] == "{" else -1 if text[i] == "}" else 0
            if depth == 0:
                candidate = text[start : i + 1]
                break
    if candidate is None:
        raise ValueError("unbalanced JSON in planner output")
    return json.loads(candidate)


def plan_via_manager(goal: str, provider: ModelProvider, model: str | None = None,
                     registry: Registry | None = None) -> Plan:
    """Have managerAS (via ``provider``) author a ``plan/v1`` for ``goal``."""
    registry = registry or Registry.load()
    catalogue = "\n".join(
        f"- {a['agent']}: {a.get('when_to_use', a.get('summary', ''))}" for a in registry.describe()
    )
    task_id = f"orchestrate-{_slug(goal)[:24]}-{uuid.uuid4().hex[:6]}"
    system = _persona("managerAS") + (
        "\n\n## PLANNING MODE\n"
        "Output ONLY a single JSON object conforming to plan/v1 — no prose, no markdown outside the "
        "JSON. Shape: {\"schema\":\"plan/v1\", \"task_id\":\"<id>\", \"goal\":\"<goal>\", "
        "\"nodes\":[{\"id\",\"agent\",\"prompt\",\"produces\",\"inputs\":[],\"depends_on\":[]}]}. "
        "Use only these agents, each for what it's best at:\n" + catalogue +
        f"\nUse task_id \"{task_id}\". Keep the plan minimal (1–4 nodes). Wire data flow with "
        "'inputs' (produced ids) and ordering with 'depends_on' (node ids)."
    )
    resp = provider.complete(system=system, messages=[ChatMessage(role="user", content=goal)],
                             model=model, temperature=0.0)
    doc = _extract_json(resp.text)
    doc.setdefault("schema", "plan/v1")
    doc.setdefault("task_id", task_id)
    doc.setdefault("goal", goal)
    plan = Plan.from_dict(doc)  # validates against plan/v1
    return plan
