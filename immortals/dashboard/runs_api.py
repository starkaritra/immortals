"""Phase-8 write half of the manager-as-a-service API (AS-031).

The read-only dashboard (:mod:`immortals.dashboard.app`) was always designed to grow write
endpoints additively — this module is that growth, kept separate so the read API stays untouched.
It adds two things to the FastAPI app:

- ``POST /api/tasks`` — submit a ``plan/v1`` and run it through the orchestrator **in a background
  thread**, returning immediately with the task id (runs are long-lived; we never block the HTTP
  request on a whole DAG).
- ``WS /ws/tasks/{task_id}`` — a live event stream. Because the orchestrator runs in a worker
  thread while WebSockets live on the async event loop, a small thread→async :class:`RunBroker`
  bridges them (``loop.call_soon_threadsafe``). On connect we replay the persisted backlog first,
  then stream live events, so a client sees the full run regardless of when it connected.

Default backend is ``mock`` (deterministic, no external calls); the real frontend passes
``backend="api"`` with a provider. Everything persists to the same event store the read API reads,
so ``GET /api/runs/{task_id}`` reflects progress and the final result.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from immortals.contracts.models import Plan
from immortals.memory import MemoryStore
from immortals.orchestrator import Orchestrator
from immortals.registry import Registry
from immortals.runners import ApiRunner, CopilotRunner, MockRunner, ToolHarness

# This module is imported by ``create_app`` only after the ``[dashboard]`` extra is confirmed, so a
# top-level FastAPI import is safe — and it puts ``WebSocket`` in module globals so FastAPI can
# resolve the (stringized, due to ``from __future__``) route annotations below.
from fastapi import Body, HTTPException, WebSocket, WebSocketDisconnect

_TERMINAL = {"completed", "failed", "blocked"}
_END = "__end__"  # synthetic control message closing a WebSocket stream


def _build_runner(opts: dict[str, Any]):
    """Construct a worker backend from request options (mirrors ``cli._make_runner``)."""
    backend = opts.get("backend", "mock")
    if backend == "mock":
        return MockRunner()
    if backend == "copilot":
        return CopilotRunner(allow_all_tools=True)
    if backend == "api":
        harness = None
        workspace = opts.get("workspace")
        if workspace:
            harness = ToolHarness(workspace, approve=(lambda a, d: True) if opts.get("approve") else None)
        return ApiRunner(opts.get("provider", "anthropic"), model=opts.get("model"), harness=harness)
    raise ValueError(f"unknown backend {backend!r}")


class RunBroker:
    """Fan out run events from the orchestrator's worker thread to async WebSocket subscribers."""

    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, task_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subs.setdefault(task_id, set()).add(q)
        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue) -> None:
        with self._lock:
            self._subs.get(task_id, set()).discard(q)

    def publish(self, task_id: str, message: dict) -> None:
        """Called from the worker thread; hands each message to the loop for every subscriber."""
        loop = self._loop
        if loop is None:
            return
        with self._lock:
            queues = list(self._subs.get(task_id, ()))
        for q in queues:
            loop.call_soon_threadsafe(q.put_nowait, message)


class RunManager:
    """Owns the broker + per-task status and starts orchestrator runs in background threads."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.broker = RunBroker()
        self.status: dict[str, str] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    def start(self, plan_doc: dict, opts: dict[str, Any]) -> str:
        plan = Plan.from_dict(plan_doc)  # validates plan/v1; raises on bad input
        task_id = plan.task_id
        with self._lock:
            if self.status.get(task_id) == "running":
                raise RuntimeError(f"task {task_id!r} is already running")
            self.status[task_id] = "running"
            t = threading.Thread(target=self._run, args=(plan, opts), name=f"run-{task_id}", daemon=True)
            self._threads[task_id] = t
        t.start()
        return task_id

    def _run(self, plan: Plan, opts: dict[str, Any]) -> None:
        store = MemoryStore(self.db_path)
        status = "failed"
        try:
            runner = _build_runner(opts)
            orch = Orchestrator(
                runner=runner,
                registry=Registry.load(),
                event_sink=lambda ev: (store.append_event(ev), self.broker.publish(plan.task_id, ev)),
                artifact_sink=store.put_artifact,
                default_workspace=opts.get("workspace"),
            )
            result = orch.run(plan)
            status = result.status
        except Exception as exc:  # noqa: BLE001 - surface as a terminal event, never crash the thread
            self.broker.publish(plan.task_id, {"schema": "event/v1", "task_id": plan.task_id,
                                               "type": "run_error", "error": str(exc)})
        finally:
            store.close()
            with self._lock:
                self.status[plan.task_id] = status
            self.broker.publish(plan.task_id, {"type": _END, "status": status})


def attach_write_api(app, db_path: str) -> RunManager:
    """Register the write endpoints on ``app`` and return the RunManager (Phase-8 seed, AS-031)."""
    manager = RunManager(db_path)

    @app.post("/api/tasks")
    def create_task(body: dict = Body(...)) -> dict[str, Any]:
        """Submit a plan/v1 and start a background orchestrator run."""
        plan_doc = body.get("plan")
        if not isinstance(plan_doc, dict):
            raise HTTPException(status_code=422, detail="body must include a 'plan' (plan/v1) object")
        opts = {k: body[k] for k in ("backend", "provider", "model", "workspace", "approve") if k in body}
        try:
            task_id = manager.start(plan_doc, opts)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except Exception as exc:  # invalid plan/v1, unknown backend, …
            raise HTTPException(status_code=422, detail=f"cannot start run: {exc}")
        return {"task_id": task_id, "status": "started"}

    @app.get("/api/tasks/{task_id}/status")
    def task_status(task_id: str) -> dict[str, Any]:
        return {"task_id": task_id, "status": manager.status.get(task_id, "unknown")}

    @app.websocket("/ws/tasks/{task_id}")
    async def stream_task(websocket: WebSocket, task_id: str) -> None:
        await websocket.accept()
        manager.broker.bind_loop(asyncio.get_running_loop())
        # Subscribe BEFORE reading the backlog so events arriving in between are queued, not lost;
        # de-dupe by event_id when we drain.
        q = manager.broker.subscribe(task_id)
        sent: set[str] = set()
        try:
            store = MemoryStore(db_path)
            try:
                backlog = store.reconstruct(task_id).events
            except KeyError:
                backlog = []
            finally:
                store.close()
            for ev in backlog:
                eid = ev.get("event_id")
                if eid not in sent:
                    await websocket.send_json(ev)
                    sent.add(eid)
            if manager.status.get(task_id) in _TERMINAL:
                await websocket.send_json({"type": _END, "status": manager.status[task_id]})
                return
            while True:
                msg = await q.get()
                if msg.get("type") == _END:
                    await websocket.send_json(msg)
                    return
                eid = msg.get("event_id")
                if eid and eid in sent:
                    continue
                await websocket.send_json(msg)
                if eid:
                    sent.add(eid)
        except WebSocketDisconnect:
            pass
        finally:
            manager.broker.unsubscribe(task_id, q)

    return manager
