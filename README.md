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
- **Memory** — local-first SQLite (append-only `event/v1` log + persisted artifacts; runs are
  reconstructable by folding the log) exposed over MCP (MCP layer in progress).

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

Status: **Phase 2** (memory substrate — event-sourced SQLite store done; MCP layer in progress).
See `design/plan.md`.
