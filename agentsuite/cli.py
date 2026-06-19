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
from agentsuite.contracts.models import Node, Plan
from agentsuite.memory import MemoryStore, ReplayResult
from agentsuite.orchestrator import Guardrails, Orchestrator, RunResult
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


def _memory_mcp_config(db_path: str) -> str:
    """JSON for `--additional-mcp-config`: a memory MCP server bound to this run's store (AS-021)."""
    config = {"mcpServers": {"agentsuite_memory": {
        "type": "local",
        "command": sys.executable,
        "args": ["-m", "agentsuite.memory.mcp_server", "--db", str(Path(db_path).resolve())],
        "tools": ["*"],
    }}}
    return json.dumps(config)


def _make_runner(backend: str, mcp_config: str | None = None,
                 env_extra: dict[str, str] | None = None) -> AgentRunner:
    if backend == "copilot":
        return CopilotRunner(allow_all_tools=True, mcp_config=mcp_config, env_extra=env_extra)
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


def _guardrails_from_args(args: argparse.Namespace) -> Guardrails:
    return Guardrails(
        max_total_tokens=args.max_tokens,
        max_wall_clock_s=args.max_seconds,
        max_nodes=args.max_nodes,
        max_agent_invocations=args.max_agent_calls,
    )


def _approval_handler(args: argparse.Namespace):
    """Resolve the approval gate per node.

    --approve auto-grants (automation mode); otherwise prompt the user interactively. With no
    TTY and no --approve, approval-required nodes are denied (the orchestrator blocks the run).
    """
    if args.approve:
        return lambda node: True

    def prompt(node: Node) -> bool:
        if not sys.stdin.isatty():
            return False
        print(
            f"[approval] node {node.id!r} ({node.agent}, reversibility={node.reversibility}) "
            f"requires sign-off. Approve? [y/N] ",
            end="",
            file=sys.stderr,
            flush=True,
        )
        return sys.stdin.readline().strip().lower() in ("y", "yes")

    return prompt


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

    store = MemoryStore(args.db) if args.db else None
    if args.resume and not store:
        print(json.dumps({"status": "failed", "error": "--resume requires --db (the persisted run)"}))
        return 2
    if args.share_memory and not args.db:
        print(json.dumps({"status": "failed", "error": "--share-memory requires --db"}))
        return 2
    partial = bool(args.from_node or args.to_node)
    if args.from_node and not store:
        print(json.dumps({"status": "failed",
                          "error": "--from requires --db to source upstream artifacts"}))
        return 2
    mcp_config = _memory_mcp_config(args.db) if (args.share_memory and args.db) else None
    env_extra = {"AGENTSUITE_MEMORY_DB": str(Path(args.db).resolve())} if (args.share_memory and args.db) else None
    runner = _make_runner(args.backend, mcp_config=mcp_config, env_extra=env_extra)
    try:
        orch = Orchestrator(
            runner=runner,
            registry=Registry.load(),
            event_sink=store.append_event if store else None,
            artifact_sink=store.put_artifact if store else None,
            guardrails=_guardrails_from_args(args),
            approval_handler=_approval_handler(args),
            max_workers=args.max_workers,
            enforce_registry_approval=args.enforce_approvals,
            default_workspace=args.workspace,
        )
        seed = store.artifacts_for(plan.task_id) if (store and (args.resume or partial)) else None
        result = orch.run(plan, resume_from=seed,
                          from_node=args.from_node, to_node=args.to_node)
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


def cmd_agents(args: argparse.Namespace) -> int:
    registry = Registry.load()
    indent = 2 if args.pretty else None
    print(json.dumps({"agents": registry.describe()}, indent=indent, default=str))
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    registry = Registry.load()
    ranked = registry.route(args.need, top=args.top)
    indent = 2 if args.pretty else None
    print(json.dumps({"need": args.need, "candidates": ranked}, indent=indent, default=str))
    return 0 if ranked else 1


MEMORY_MCP_SERVER_NAME = "agentsuite-memory"


def _user_mcp_config_path(args: argparse.Namespace) -> Path:
    if getattr(args, "config_path", None):
        return Path(args.config_path)
    return Path.home() / ".copilot" / "mcp-config.json"


def cmd_memory(args: argparse.Namespace) -> int:
    """Register/unregister the env-resolved memory MCP server in the persistent copilot config.

    Persistent registration is the channel that reaches custom `--agent` workers (AS-021/R7). The
    server reads its store from ``$AGENTSUITE_MEMORY_DB``, which `run --share-memory` sets per run.
    """
    path = _user_mcp_config_path(args)
    config: dict[str, Any] = {}
    if path.exists():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(json.dumps({"status": "failed", "error": f"existing config is not valid JSON: {exc}"}))
            return 2
    servers = config.setdefault("mcpServers", {})

    if args.memory_action == "status":
        entry = servers.get(MEMORY_MCP_SERVER_NAME)
        print(json.dumps({"registered": entry is not None, "config_path": str(path),
                          "entry": entry}, indent=2))
        return 0

    if args.memory_action == "register":
        servers[MEMORY_MCP_SERVER_NAME] = {
            "type": "local",
            "command": sys.executable,
            "args": ["-m", "agentsuite.memory.mcp_server"],
            "tools": ["*"],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print(json.dumps({"status": "registered", "server": MEMORY_MCP_SERVER_NAME,
                          "config_path": str(path),
                          "note": "set AGENTSUITE_MEMORY_DB per run (run --share-memory does this)"}))
        return 0

    if args.memory_action == "unregister":
        existed = servers.pop(MEMORY_MCP_SERVER_NAME, None) is not None
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print(json.dumps({"status": "unregistered" if existed else "not_present",
                          "config_path": str(path)}))
        return 0

    print(json.dumps({"status": "failed", "error": f"unknown memory action {args.memory_action!r}"}))
    return 2


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
    run.add_argument("--share-memory", action="store_true",
                     help="Inject a memory MCP server (bound to --db) into workers so they share memory.")
    run.add_argument("--max-tokens", type=int, help="Cap cumulative tokens across the run (guardrail).")
    run.add_argument("--max-seconds", type=float, help="Wall-clock budget for the whole run (guardrail).")
    run.add_argument("--max-nodes", type=int, help="Cap the number of node executions (guardrail).")
    run.add_argument("--max-agent-calls", type=int, help="Cap invocations of any single agent (loop guard).")
    run.add_argument("--approve", action="store_true",
                     help="Auto-approve approval-required nodes (automation mode).")
    run.add_argument("--enforce-approvals", action="store_true",
                     help="Apply each agent manifest's approval_default as a sign-off floor (registry-driven).")
    run.add_argument("--resume", action="store_true",
                     help="Skip nodes already completed in the --db store (resume an interrupted run).")
    run.add_argument("--max-workers", type=int, default=1,
                     help="Run independent DAG nodes concurrently, up to this many (default 1 = sequential).")
    run.add_argument("--from", dest="from_node", metavar="NODE",
                     help="Partial re-run: execute NODE and everything downstream (needs --db for upstream).")
    run.add_argument("--to", dest="to_node", metavar="NODE",
                     help="Partial re-run: execute only NODE and its upstream dependencies.")
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

    agents = sub.add_parser("agents", help="List registered agent manifests (the routing catalogue).")
    agents.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    agents.set_defaults(func=cmd_agents)

    route = sub.add_parser("route", help="Rank agents against a free-text or capability need.")
    route.add_argument("--need", required=True, help="Task need / capability to match against manifests.")
    route.add_argument("--top", type=int, help="Return at most this many candidates.")
    route.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    route.set_defaults(func=cmd_route)

    memory = sub.add_parser("memory",
                            help="Manage the persistent memory MCP server registration (shared worker memory).")
    memory.add_argument("memory_action", choices=["register", "unregister", "status"],
                        help="register/unregister the memory MCP server in the copilot config, or show status.")
    memory.add_argument("--config-path", help="Override the copilot mcp-config path (default: ~/.copilot/mcp-config.json).")
    memory.set_defaults(func=cmd_memory)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
