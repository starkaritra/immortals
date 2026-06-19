"""AgentSuite CLI — the orchestrator seam managerAS invokes (decision AS-013).

`python -m agentsuite run --plan-file plan.json` validates a ``plan/v1``, executes it through
the deterministic orchestrator, and prints a JSON result (artifacts + status + events) to
stdout. managerAS calls this as a tool; it is also usable standalone for testing/dry-runs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agentsuite.contracts import ContractError
from agentsuite.contracts.models import Plan
from agentsuite.memory import MemoryStore, ReplayResult
from agentsuite.orchestrator import Orchestrator, RunResult
from agentsuite.orchestrator.runner import PlanError
from agentsuite.registry import Registry
from agentsuite.runners import CopilotRunner, MockRunner
from agentsuite.runners.base import AgentRunner


def _load_plan_source(args: argparse.Namespace) -> dict[str, Any]:
    if args.plan_file:
        text = Path(args.plan_file).read_text(encoding="utf-8")
    elif args.plan:
        text = args.plan
    else:  # stdin
        text = sys.stdin.read()
    if not text.strip():
        raise SystemExit("error: empty plan input (use --plan-file, --plan, or pipe to stdin)")
    return json.loads(text)


def _make_runner(backend: str) -> AgentRunner:
    if backend == "copilot":
        return CopilotRunner(allow_all_tools=True)
    if backend == "mock":
        return MockRunner()
    raise SystemExit(f"error: unknown backend {backend!r}")


def result_to_dict(result: RunResult, include_events: bool) -> dict[str, Any]:
    out: dict[str, Any] = {
        "task_id": result.task_id,
        "status": result.status,
        "artifacts": {aid: art.to_dict() for aid, art in result.artifacts.items()},
    }
    if result.failed_node:
        out["failed_node"] = result.failed_node
    if result.error:
        out["error"] = result.error
    if include_events:
        out["events"] = result.events
    else:
        out["event_count"] = len(result.events)
    return out


def cmd_run(args: argparse.Namespace) -> int:
    try:
        plan_dict = _load_plan_source(args)
        plan = Plan.from_dict(plan_dict)
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "failed", "error": f"invalid JSON: {exc}"}))
        return 2
    except ContractError as exc:
        print(json.dumps({"status": "failed", "error": f"plan/v1 invalid: {exc}"}))
        return 2

    runner = _make_runner(args.backend)
    store = MemoryStore(args.db) if args.db else None
    try:
        orch = Orchestrator(
            runner=runner,
            registry=Registry.load(),
            event_sink=store.append_event if store else None,
            artifact_sink=store.put_artifact if store else None,
            default_workspace=args.workspace,
        )
        result = orch.run(plan)
    except PlanError as exc:
        print(json.dumps({"status": "failed", "error": f"plan rejected: {exc}"}))
        return 2
    finally:
        if store:
            store.close()

    indent = 2 if args.pretty else None
    print(json.dumps(result_to_dict(result, args.events), indent=indent, default=str))
    return 0 if result.status == "completed" else 1


def _replay_to_dict(result: ReplayResult, include_events: bool) -> dict[str, Any]:
    out: dict[str, Any] = {
        "task_id": result.task_id,
        "status": result.status,
        "artifacts": {aid: art.to_dict() for aid, art in result.artifacts.items()},
    }
    if result.failed_node:
        out["failed_node"] = result.failed_node
    if include_events:
        out["events"] = result.events
    else:
        out["event_count"] = len(result.events)
    return out


def cmd_replay(args: argparse.Namespace) -> int:
    store = MemoryStore(args.db)
    try:
        if args.list:
            print(json.dumps({"tasks": store.tasks()}, indent=2 if args.pretty else None))
            return 0
        if not args.task_id:
            print(json.dumps({"status": "failed", "error": "provide --task-id or --list"}))
            return 2
        try:
            result = store.reconstruct(args.task_id)
        except KeyError as exc:
            print(json.dumps({"status": "failed", "error": str(exc)}))
            return 2
        indent = 2 if args.pretty else None
        print(json.dumps(_replay_to_dict(result, args.events), indent=indent, default=str))
        return 0 if result.status == "completed" else 1
    finally:
        store.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentsuite", description="AgentSuite orchestrator CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Execute a plan/v1 through the orchestrator.")
    src = run.add_mutually_exclusive_group()
    src.add_argument("--plan-file", help="Path to a plan/v1 JSON file.")
    src.add_argument("--plan", help="Inline plan/v1 JSON string.")
    run.add_argument("--backend", choices=["copilot", "mock"], default="copilot",
                     help="Invocation backend (default: copilot).")
    run.add_argument("--workspace", help="Directory workers may access (--add-dir).")
    run.add_argument("--db", help="SQLite path to persist the event log + artifacts (event-sourced run).")
    run.add_argument("--events", action="store_true", help="Include the full event trail in output.")
    run.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    run.set_defaults(func=cmd_run)

    replay = sub.add_parser("replay", help="Reconstruct a run by folding its persisted event log.")
    replay.add_argument("--db", required=True, help="SQLite path written by `run --db`.")
    replay.add_argument("--task-id", help="Task to reconstruct.")
    replay.add_argument("--list", action="store_true", help="List task ids in the store.")
    replay.add_argument("--events", action="store_true", help="Include the full event trail in output.")
    replay.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    replay.set_defaults(func=cmd_replay)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
