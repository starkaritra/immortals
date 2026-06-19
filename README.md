# AgentSuite

A manager-orchestrated multi-agent system over the **AS agent suite** (coderAS, experimentAS,
teachAS, prepAS, researchAS, paperAS, patentAS, presentAS, discussAS, …).

- **managerAS** — the single user-facing agent. Turns a task (structured or vague) into a
  typed **plan** (a DAG of agent calls), routes each node to the right specialist, holds a
  quality bar, re-plans on failure, and synthesizes the result.
- **Orchestrator** (`agentsuite/`) — deterministic Python. Validates the plan, executes the
  DAG, validates every seam contract, runs guardrails, and mediates all inter-agent I/O.
- **Workers** — the existing `~/.copilot/agents/*.md` personas, invoked through a swappable
  `AgentRunner` (Backend A = headless `copilot` today; LangGraph/ACP later).
- **Memory** — local-first SQLite (append-only `event/v1` log + persisted artifacts + a shared
  `notes` KV; runs are reconstructable by folding the log), exposed over a zero-dep MCP server.

See `design/architecture.md` (target spec), `design/plan.md` (build order), and
`design/handoff.md` (state + decision log AS-001…AS-012).

## Contracts (the architecture)
Versioned JSON, validated at every seam — in `agentsuite/contracts/schemas/`:
`plan/v1`, `artifact/v1`, `registry/v1`, `event/v1`.

## Develop
```pwsh
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

Status: **Phases 0–5 + memory MCP** (orchestrator, guardrails, resume/parallel/partial re-runs,
registry routing, event-sourced memory + MCP server). See `design/plan.md`.

## Shared worker memory (MCP)
The event-sourced store is exposed as a zero-dependency MCP server
(`agentsuite/memory/mcp_server.py`) offering `memory_{get_artifact,list_artifacts,put_note,
get_note,list_notes,recent_events}`. `run --db <path> --share-memory` injects it (bound to the
run's store) and sets `AGENTSUITE_MEMORY_DB` for the worker. Register it persistently for the
default agent / interactive sessions with `agentsuite memory register` (reversible via
`agentsuite memory unregister`).

**Known CLI limitation (R7, AS-022):** in headless `-p` mode the copilot CLI exposes MCP tools to
the *default* agent but **not to custom `--agent` workers** — verified for both `--additional-mcp-config`
and persistent registration (the server connects, but its tools aren't in a custom agent's toolset).
Because AgentSuite workers are always custom agents, **worker-initiated** shared memory is currently
blocked by the CLI. Today the orchestrator remains the central writer (every worker artifact + event
is persisted to the shared store, so cross-run memory and audit are intact); worker-shared
read/write will be delivered by the orchestrator acting as the **memory broker** (inject relevant
memory into prompts; persist worker-declared notes) rather than via worker-side MCP calls.
