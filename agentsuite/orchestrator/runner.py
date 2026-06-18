"""The deterministic DAG executor."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from agentsuite.contracts import validate, ContractError
from agentsuite.contracts.models import Plan, Node, Artifact
from agentsuite.registry import Registry
from agentsuite.runners.base import AgentRunner, RunRequest, RunnerError

EventSink = Callable[[dict], None]


class PlanError(ValueError):
    """Raised when a plan is structurally invalid (bad schema, unknown agent, cycle, dangling input)."""


@dataclass
class RunResult:
    task_id: str
    status: str  # "completed" | "failed"
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    failed_node: str | None = None
    error: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Orchestrator:
    def __init__(
        self,
        runner: AgentRunner,
        registry: Registry | None = None,
        event_sink: EventSink | None = None,
        default_workspace: str | None = None,
    ):
        self.runner = runner
        self.registry = registry if registry is not None else Registry.load()
        self.event_sink = event_sink
        self.default_workspace = default_workspace

    # -- public API --------------------------------------------------------------------

    def run(self, plan: Plan | dict) -> RunResult:
        plan = plan if isinstance(plan, Plan) else Plan.from_dict(plan)
        events: list[dict] = []
        counter = {"n": 0}

        def emit(etype: str, **fields: Any) -> None:
            counter["n"] += 1
            ev = {
                "schema": "event/v1",
                "event_id": f"{plan.task_id}-{counter['n']}",
                "task_id": plan.task_id,
                "ts": _now(),
                "type": etype,
            }
            ev.update({k: v for k, v in fields.items() if v is not None})
            validate(ev, "event/v1")
            events.append(ev)
            if self.event_sink:
                self.event_sink(ev)

        self._validate_plan(plan)
        emit("plan_validated", payload={"nodes": len(plan.nodes)})

        order = self._topo_order(plan)
        blackboard: dict[str, Artifact] = {}

        for node_id in order:
            node = plan.node(node_id)
            emit("node_started", node_id=node.id, agent=node.agent)
            request = self._build_request(plan, node, blackboard)
            try:
                artifact = self.runner.run(request)
            except RunnerError as exc:
                emit("node_failed", node_id=node.id, agent=node.agent, payload={"error": str(exc)})
                emit("escalation", node_id=node.id, payload={"reason": "runner_error"})
                return RunResult(plan.task_id, "failed", blackboard, events, node.id, str(exc))

            # Seam contract validation.
            try:
                self._validate_seam(node, artifact)
            except ContractError as exc:
                emit("node_failed", node_id=node.id, agent=node.agent, payload={"error": str(exc)})
                emit("escalation", node_id=node.id, payload={"reason": "contract_violation"})
                return RunResult(plan.task_id, "failed", blackboard, events, node.id, str(exc))

            if artifact.status == "failed":
                emit("node_failed", node_id=node.id, agent=node.agent,
                     payload={"error": artifact.error or "agent reported failure"})
                emit("escalation", node_id=node.id, payload={"reason": "agent_failed"})
                return RunResult(plan.task_id, "failed", blackboard, events, node.id, artifact.error)

            blackboard[artifact.id] = artifact
            emit("artifact_written", node_id=node.id, agent=node.agent, payload={"artifact_id": artifact.id})
            emit("node_completed", node_id=node.id, agent=node.agent)

        emit("run_completed", payload={"artifacts": sorted(blackboard)})
        return RunResult(plan.task_id, "completed", blackboard, events)

    # -- validation & scheduling -------------------------------------------------------

    def _validate_plan(self, plan: Plan) -> None:
        plan.validate()  # schema
        produced_by: dict[str, str] = {}
        for node in plan.nodes:
            if node.agent not in self.registry:
                raise PlanError(
                    f"node {node.id!r} routes to unregistered agent {node.agent!r}; "
                    f"known: {self.registry.agents()}"
                )
            if node.produces in produced_by:
                raise PlanError(
                    f"artifact id {node.produces!r} produced by both "
                    f"{produced_by[node.produces]!r} and {node.id!r}"
                )
            produced_by[node.produces] = node.id
        # Every declared input must be produced by some node.
        for node in plan.nodes:
            for art_id in node.inputs:
                if art_id not in produced_by:
                    raise PlanError(
                        f"node {node.id!r} consumes {art_id!r}, which no node produces"
                    )

    def _topo_order(self, plan: Plan) -> list[str]:
        produced_by = {n.produces: n.id for n in plan.nodes}
        deps: dict[str, set[str]] = {n.id: set() for n in plan.nodes}
        # Data dependencies: a node depends on the producers of its inputs.
        for node in plan.nodes:
            for art_id in node.inputs:
                deps[node.id].add(produced_by[art_id])
        # Explicit control edges (from -> to means "to depends on from").
        for edge in plan.edges:
            if edge.to in deps and edge.from_ in deps:
                deps[edge.to].add(edge.from_)

        order: list[str] = []
        resolved: set[str] = set()
        # Stable Kahn's algorithm: preserve plan node order among ready nodes.
        node_seq = [n.id for n in plan.nodes]
        while len(order) < len(node_seq):
            ready = [n for n in node_seq if n not in resolved and deps[n] <= resolved]
            if not ready:
                remaining = [n for n in node_seq if n not in resolved]
                raise PlanError(f"plan has a dependency cycle among nodes: {remaining}")
            for n in ready:
                order.append(n)
                resolved.add(n)
        return order

    def _build_request(self, plan: Plan, node: Node, blackboard: dict[str, Artifact]) -> RunRequest:
        inputs = {aid: blackboard[aid] for aid in node.inputs if aid in blackboard}
        return RunRequest(
            agent=node.agent,
            node_id=node.id,
            task_id=plan.task_id,
            prompt=node.prompt,
            produces=node.produces,
            inputs=inputs,
            context={"goal": plan.goal, "success_criteria": node.success_criteria}
            if node.success_criteria
            else {"goal": plan.goal},
            workspace=self.default_workspace,
            max_tokens=node.budget.get("max_tokens"),
            timeout_s=node.budget.get("timeout_s"),
        )

    def _validate_seam(self, node: Node, artifact: Artifact) -> None:
        artifact.validate()  # artifact/v1 schema
        if artifact.id != node.produces:
            raise ContractError(
                f"node {node.id!r} declared produces={node.produces!r} but artifact id is {artifact.id!r}"
            )
        if artifact.node_id != node.id or artifact.produced_by != node.agent:
            raise ContractError(
                f"artifact provenance mismatch for node {node.id!r}: "
                f"node_id={artifact.node_id!r}, produced_by={artifact.produced_by!r}"
            )
