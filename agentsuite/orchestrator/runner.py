"""The deterministic DAG executor."""

from __future__ import annotations

import time
import uuid
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from agentsuite.contracts import validate, ContractError
from agentsuite.contracts.models import Plan, Node, Artifact
from agentsuite.registry import Registry
from agentsuite.runners.base import AgentRunner, RunRequest, RunnerError
from .guardrails import ApprovalHandler, Guardrails, GuardrailBreach, GuardrailState

EventSink = Callable[[dict], None]
ArtifactSink = Callable[["Artifact"], None]


class PlanError(ValueError):
    """Raised when a plan is structurally invalid (bad schema, unknown agent, cycle, dangling input)."""


@dataclass
class RunResult:
    task_id: str
    status: str  # "completed" | "failed" | "blocked"
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    failed_node: str | None = None
    error: str | None = None


@dataclass
class _Failure:
    """An internal signal that a node ended the run (failed or blocked)."""

    node_id: str
    status: str  # "failed" | "blocked"
    error: str | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Orchestrator:
    def __init__(
        self,
        runner: AgentRunner,
        registry: Registry | None = None,
        event_sink: EventSink | None = None,
        artifact_sink: ArtifactSink | None = None,
        guardrails: Guardrails | None = None,
        approval_handler: ApprovalHandler | None = None,
        max_workers: int = 1,
        default_workspace: str | None = None,
    ):
        self.runner = runner
        self.registry = registry if registry is not None else Registry.load()
        self.event_sink = event_sink
        self.artifact_sink = artifact_sink
        self.guardrails = guardrails or Guardrails()
        self.approval_handler = approval_handler
        self.max_workers = max(1, int(max_workers))
        self.default_workspace = default_workspace

    # -- public API --------------------------------------------------------------------

    def run(
        self,
        plan: Plan | dict,
        resume_from: dict[str, Artifact] | None = None,
        from_node: str | None = None,
        to_node: str | None = None,
    ) -> RunResult:
        plan = plan if isinstance(plan, Plan) else Plan.from_dict(plan)
        events: list[dict] = []
        counter = {"n": 0}
        run_id = uuid.uuid4().hex[:12]

        def emit(etype: str, **fields: Any) -> None:
            counter["n"] += 1
            ev = {
                "schema": "event/v1",
                "event_id": f"{plan.task_id}-{run_id}-{counter['n']}",
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
        emit("plan_validated", payload={"nodes": len(plan.nodes), "run_id": run_id})

        order = self._topo_order(plan)
        deps = self._node_deps(plan)
        # Resume / partial re-run: seed the blackboard with already-produced artifacts.
        blackboard: dict[str, Artifact] = dict(resume_from) if resume_from else {}
        state = GuardrailState(self.guardrails)
        started_at = time.monotonic()

        done: set[str] = set()
        worklist: list[str] = []
        if from_node is not None or to_node is not None:
            # Partial re-run: execute only the selected sub-graph; force-run it (no resume-skip).
            selection = self._select_nodes(plan, deps, from_node, to_node)
            produced_in_sel = {plan.node(n).produces for n in selection}
            for nid in selection:
                for art_id in plan.node(nid).inputs:
                    if art_id not in blackboard and art_id not in produced_in_sel:
                        raise PlanError(
                            f"partial re-run of {nid!r} needs input {art_id!r}, which is neither "
                            f"in the seeded store nor produced by a selected node; widen --from/--to "
                            f"or run the upstream nodes first"
                        )
            emit("decision", payload={"partial_run": {
                "from": from_node, "to": to_node, "selected": sorted(selection)}})
            # Non-selected nodes are out of scope: treat them as resolved (deps satisfied from store).
            done = {n.id for n in plan.nodes if n.id not in selection}
            worklist = [n for n in order if n in selection]
        else:
            # Resume bookkeeping: a node whose output is already persisted is skipped (idempotent).
            for node_id in order:
                node = plan.node(node_id)
                if node.produces in blackboard:
                    emit("node_completed", node_id=node.id, agent=node.agent,
                         payload={"skipped": "resumed"})
                    done.add(node_id)
                else:
                    worklist.append(node_id)

        # The two helpers below run on the main thread only; in the parallel path the thread pool
        # executes nothing but ``runner.run`` — all event emission, persistence, and guardrail
        # accounting stay single-threaded, so no shared state needs locking.
        def gate_and_reserve(node: Node) -> _Failure | None:
            """Approval gate (AS-005) + pre-invoke guardrail reservation (deadline/node/agent caps)."""
            if node.approval == "required":
                emit("approval_requested", node_id=node.id, agent=node.agent,
                     payload={"reversibility": node.reversibility})
                granted = self.approval_handler(node) if self.approval_handler else False
                if not granted:
                    reason = "approval_denied" if self.approval_handler else "approval_required"
                    emit("escalation", node_id=node.id, payload={"reason": reason})
                    return _Failure(node.id, "blocked",
                                    f"node {node.id!r} requires approval ({reason})")
                emit("approval_granted", node_id=node.id, agent=node.agent)
            try:
                state.before_node(node.agent, time.monotonic() - started_at)
            except GuardrailBreach as breach:
                emit("node_failed", node_id=node.id, agent=node.agent,
                     payload={"error": breach.message})
                emit("escalation", node_id=node.id, payload={"reason": breach.reason})
                return _Failure(node.id, "failed", breach.message)
            emit("node_started", node_id=node.id, agent=node.agent)
            return None

        def finalize(node: Node, artifact: Artifact) -> _Failure | None:
            """Seam validation + persistence + post-invoke token accounting."""
            try:
                self._validate_seam(node, artifact)
            except ContractError as exc:
                emit("node_failed", node_id=node.id, agent=node.agent, payload={"error": str(exc)})
                emit("escalation", node_id=node.id, payload={"reason": "contract_violation"})
                return _Failure(node.id, "failed", str(exc))
            if artifact.status == "failed":
                emit("node_failed", node_id=node.id, agent=node.agent,
                     payload={"error": artifact.error or "agent reported failure"})
                emit("escalation", node_id=node.id, payload={"reason": "agent_failed"})
                return _Failure(node.id, "failed", artifact.error)
            blackboard[artifact.id] = artifact
            if self.artifact_sink:
                self.artifact_sink(artifact)
            emit("artifact_written", node_id=node.id, agent=node.agent,
                 payload={"artifact_id": artifact.id})
            emit("node_completed", node_id=node.id, agent=node.agent)
            try:
                state.after_node(artifact)
            except GuardrailBreach as breach:
                emit("node_failed", node_id=node.id, agent=node.agent,
                     payload={"error": breach.message})
                emit("escalation", node_id=node.id, payload={"reason": breach.reason})
                return _Failure(node.id, "failed", breach.message)
            return None

        def run_node(node: Node) -> Artifact:
            return self.runner.run(self._build_request(plan, node, blackboard))

        if self.max_workers > 1:
            failure = self._run_parallel(plan, worklist, deps, done, emit,
                                         gate_and_reserve, finalize, run_node)
        else:
            failure = self._run_sequential(plan, worklist, emit,
                                           gate_and_reserve, finalize, run_node)

        if failure is not None:
            return RunResult(plan.task_id, failure.status, blackboard, events,
                             failure.node_id, failure.error)
        emit("run_completed", payload={"artifacts": sorted(blackboard)})
        return RunResult(plan.task_id, "completed", blackboard, events)

    # -- execution paths ---------------------------------------------------------------

    def _run_sequential(self, plan, worklist, emit, gate, finalize, run_node) -> _Failure | None:
        for node_id in worklist:
            node = plan.node(node_id)
            fail = gate(node)
            if fail is not None:
                return fail
            try:
                artifact = run_node(node)
            except RunnerError as exc:
                emit("node_failed", node_id=node.id, agent=node.agent, payload={"error": str(exc)})
                emit("escalation", node_id=node.id, payload={"reason": "runner_error"})
                return _Failure(node.id, "failed", str(exc))
            fail = finalize(node, artifact)
            if fail is not None:
                return fail
        return None

    def _run_parallel(self, plan, worklist, deps, done, emit, gate, finalize, run_node) -> _Failure | None:
        """Readiness scheduler: submit ready nodes (deps resolved) to a bounded thread pool.

        Only ``run_node`` (the slow ``runner.run``) executes off the main thread; ``gate`` and
        ``finalize`` are invoked here on the main thread, so the blackboard, event log, and
        guardrail state are never touched concurrently.
        """
        pending: list[str] = list(worklist)
        in_flight: dict[Future, Node] = {}
        failure: _Failure | None = None
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while (pending or in_flight) and failure is None:
                # Schedule every ready node up to the worker budget (stable plan order).
                for node_id in list(pending):
                    if len(in_flight) >= self.max_workers:
                        break
                    if not deps[node_id] <= done:
                        continue
                    node = plan.node(node_id)
                    fail = gate(node)  # approval + pre-invoke guardrails (main thread)
                    pending.remove(node_id)
                    if fail is not None:
                        failure = fail
                        break
                    in_flight[pool.submit(run_node, node)] = node
                if failure is not None:
                    break
                if not in_flight:
                    break  # nothing ready and nothing running (validated DAG ⇒ no progress left)
                completed, _ = wait(in_flight, return_when=FIRST_COMPLETED)
                for fut in completed:
                    node = in_flight.pop(fut)
                    try:
                        artifact = fut.result()
                    except RunnerError as exc:
                        emit("node_failed", node_id=node.id, agent=node.agent,
                             payload={"error": str(exc)})
                        emit("escalation", node_id=node.id, payload={"reason": "runner_error"})
                        failure = failure or _Failure(node.id, "failed", str(exc))
                        continue
                    fail = finalize(node, artifact)
                    if fail is not None:
                        failure = failure or fail
                    else:
                        done.add(node.id)
            if in_flight:
                wait(in_flight)  # let started workers drain so threads don't outlive the run
        return failure

    # -- validation & scheduling -------------------------------------------------------

    def _validate_plan(self, plan: Plan) -> None:
        plan.validate()  # schema
        node_ids = {n.id for n in plan.nodes}
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
        for node in plan.nodes:
            # Every declared input must be produced by some node.
            for art_id in node.inputs:
                if art_id not in produced_by:
                    raise PlanError(
                        f"node {node.id!r} consumes {art_id!r}, which no node produces"
                    )
            # Every explicit dependency must reference a real node.
            for dep in node.depends_on:
                if dep not in node_ids:
                    raise PlanError(
                        f"node {node.id!r} depends_on {dep!r}, which is not a node in the plan"
                    )

    def _node_deps(self, plan: Plan) -> dict[str, set[str]]:
        """Prerequisite node ids for each node: input producers + depends_on + control edges."""
        produced_by = {n.produces: n.id for n in plan.nodes}
        deps: dict[str, set[str]] = {n.id: set() for n in plan.nodes}
        for node in plan.nodes:
            for art_id in node.inputs:
                deps[node.id].add(produced_by[art_id])
            deps[node.id].update(node.depends_on)
        for edge in plan.edges:
            if edge.to in deps and edge.from_ in deps:
                deps[edge.to].add(edge.from_)
        return deps

    def _select_nodes(self, plan: Plan, deps: dict[str, set[str]],
                      from_node: str | None, to_node: str | None) -> set[str]:
        """Nodes to execute for a partial re-run: descendants of ``from`` ∩ ancestors of ``to``."""
        node_ids = {n.id for n in plan.nodes}
        for label, nid in (("--from", from_node), ("--to", to_node)):
            if nid is not None and nid not in node_ids:
                raise PlanError(f"{label} references {nid!r}, which is not a node in the plan")

        dependents: dict[str, set[str]] = {n.id: set() for n in plan.nodes}
        for nid, prereqs in deps.items():
            for dep in prereqs:
                dependents[dep].add(nid)

        def _reach(start: str, adjacency: dict[str, set[str]]) -> set[str]:
            seen = {start}
            stack = [start]
            while stack:
                cur = stack.pop()
                for nxt in adjacency[cur]:
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
            return seen

        selection = set(node_ids)
        if from_node is not None:
            selection &= _reach(from_node, dependents)   # from + everything downstream
        if to_node is not None:
            selection &= _reach(to_node, deps)            # to + everything upstream
        if not selection:
            raise PlanError(
                f"no nodes selected by --from={from_node!r}/--to={to_node!r} "
                f"(no dependency path connects them)"
            )
        return selection

    def _topo_order(self, plan: Plan) -> list[str]:
        deps = self._node_deps(plan)
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
