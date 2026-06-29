# Immortals — Architecture

## North star
A single user-facing **managerAS** takes a task (structured or vague), decomposes it into a
**typed, validated plan**, and a **deterministic orchestrator** executes that plan by invoking
the existing `AS` worker agents (coderAS, experimentAS, teachAS, prepAS, researchAS, paperAS,
patentAS, presentAS, discussAS, …), routing typed artifacts between them through shared
memory. The orchestrator owns the *mechanism*; the agents own the *domain work*; the manager
owns the *intelligence* of decomposition and synthesis. Every run is reproducible and
replayable.

Guiding principle (inherited from `eval_platform`): **ship mechanism, not forks.** Differences
between tasks and agents are expressed as *data* (plans, manifests, config), never as
forked orchestrator code.

## Roles

| Role | Responsibility | Determinism |
|---|---|---|
| **managerAS** (planner/router/aggregator) | The *only* user-facing agent. Turns a task into a validated plan; re-plans on escalation; synthesizes the final answer. | LLM policy |
| **Orchestrator** (`immortals/`) | Validates the plan, executes the DAG, enforces seam contracts, runs guardrails, mediates all I/O, escalates to the manager only at defined decision points. | Deterministic mechanism |
| **Worker agents** (`~/.copilot/agents/*.md`) | Do the actual domain work; read declared inputs, write one typed artifact. | LLM, sandboxed per call |
| **Memory** (local SQLite + MCP) | Source-of-truth event log; derived graph + vector + KV read models; per-agent + universal stores. | Deterministic substrate |

## Component map

```
                ┌──────────────┐
   user ───────▶│  managerAS   │  (only user-facing agent; planner + aggregator)
                └──────┬───────┘
                       │ emits  Plan (typed DAG)            ▲ escalation (failure / contract
                       ▼                                    │ violation / ambiguity → re-plan)
                ┌──────────────────────────────────────────┴───────┐
                │              Orchestrator  (Python)               │
                │  plan validate → topo schedule → seam contracts   │
                │  → guardrails → aggregate                         │
                └───┬───────────────┬───────────────┬──────────────┘
                    │ AgentRunner    │               │  read/write artifacts + events
                    ▼ (swappable)    ▼               ▼
            ┌───────────────┐ ┌───────────────┐ ┌───────────────────────────────┐
            │  Backend A    │ │  Backend C    │ │   Memory MCP server (local)   │
            │ copilot -p    │ │ LangGraph/ACP │ │  event log │ graph │ vector   │
            │ --agent X     │ │  (future)     │ │  │ KV │ per-agent │ universal │
            └──────┬────────┘ └───────────────┘ └───────────────────────────────┘
                   ▼
          worker agent run (coderAS, experimentAS, …) → one typed Artifact
```

## Core contracts (versioned JSON, validated at every seam)

The contracts are the architecture. Everything else is replaceable behind them.

### Plan (`plan/v1`)
A directed acyclic graph the manager emits and the orchestrator executes.
```json
{
  "schema": "plan/v1",
  "task_id": "…",
  "goal": "free-text user goal",
  "nodes": [
    {
      "id": "design",
      "agent": "experimentAS",
      "prompt": "…",
      "inputs": [],                 // artifact ids this node consumes
      "produces": "design.artifact",// artifact id this node emits
      "context_refs": ["fact:123"], // memory refs, NOT inlined blobs
      "approval": "required|none",  // human-in-the-loop gate
      "budget": { "max_tokens": 40000, "timeout_s": 600 }
    }
  ],
  "edges": [ { "from": "design", "to": "implement", "on": "success" } ]
}
```
Rationale for a DAG (not a flat list): tasks have dependencies, parallelism, and data flow
between agents. Inputs/outputs are referenced **by artifact id**, never inline-copied — this
keeps provenance and avoids context bloat.

### Artifact (`artifact/v1`)
The typed output every agent produces; the only currency between agents (the *blackboard*).
```json
{
  "schema": "artifact/v1",
  "id": "design.artifact",
  "produced_by": "experimentAS",
  "node_id": "design",
  "task_id": "…",
  "type": "experiment_design|code_change|report|critique|…",
  "content": { "…": "typed per artifact type" },
  "provenance": { "model": "…", "session_id": "…", "started": "…", "ended": "…", "cost": {…} },
  "status": "ok|partial|failed",
  "untrusted": true
}
```
**Artifacts are data, never instructions.** A downstream agent treats an upstream artifact's
content as untrusted input (prompt-injection containment), mediated by the orchestrator.

### Agent manifest (`registry/v1`) — capability registry
Machine-readable description of each agent, in `registry/`. The manager routes by *matching
task requirements to agent contracts*, not by hardcoded logic. Adding an agent = adding a
manifest.
```json
{
  "schema": "registry/v1",
  "agent": "experimentAS",
  "summary": "Designs/conducts/analyzes rigorous experiments.",
  "capabilities": ["experiment_design", "statistical_analysis", "ab_test", "ablation"],
  "consumes": ["hypothesis", "dataset_ref", "code_change"],
  "produces": ["experiment_design", "analysis_report"],
  "approval_default": "required",
  "cost_hint": "medium",
  "when_to_use": "validate/verify a hypothesis, product, or design choice"
}
```

### Event (`event/v1`) — the source of truth
Every invocation, input, output, decision, and escalation is an immutable append-only event.
The orchestrator's state is a fold over the event log; the graph and vector stores are
projections of it. Enables replay, audit, and reproducible runs.

## Execution model
1. **Plan** — manager emits `plan/v1`; orchestrator validates it against the schema **and**
   against the capability registry (every node's `agent`, `inputs`, `produces` must type-check).
   Invalid plans are rejected back to the manager.
2. **Schedule** — topological order; independent nodes run in parallel (bounded by
   `--max-workers`).
3. **Invoke** — for each node, the orchestrator calls `AgentRunner.run(...)`, supplying only
   the declared inputs (resolved from the blackboard) + memory refs.
4. **Validate seam** — the returned artifact is validated against its declared type/contract
   before any downstream node may consume it (the `eval_platform` "entry-seam contract" rule).
5. **Escalate (only at defined points)** — on failure, contract violation, or flagged
   ambiguity, control returns to the manager for re-planning. Determinism in the control flow;
   LLM judgment only where explicitly permitted.
6. **Guardrails** — budget/token caps, max delegation depth, loop detection, timeouts, and
   approval gates are enforced by the orchestrator around every node.
7. **Aggregate** — manager synthesizes the final user-facing answer from the terminal
   artifacts.

## AgentRunner abstraction (swappable invocation backends)
A single interface decouples *what to run* from *how it's run*:
`AgentRunner.run(agent, prompt, inputs, context_refs, limits) -> Artifact`.

- **Backend A — headless Copilot CLI (current).** Each worker is a real `copilot` process:
  `copilot --agent <name> -p "<prompt>" --output-format json --allow-all-tools --no-ask-user
  --add-dir <workspace> --additional-mcp-config @memory.json [--session-id … | --resume …]`.
  Output is JSONL (parsed into the artifact); `--session-id`/`--resume` give continuity and
  replay; `--secret-env-vars` redacts secrets. Reuses the existing `.md` personas verbatim.
- **Backend C — durable framework / ACP (future).** LangGraph (or the CLI's `--acp` Agent
  Client Protocol server) for durable execution, checkpointing, and richer interrupts. The
  personas are reused; only the runner changes.

The plan schema, memory, registry, and guardrails are **invocation-agnostic** — backends swap
without touching them.

## Memory architecture
Layered, with a CQRS-style substrate (append events; project into read models).

| Layer | Contents | Store |
|---|---|---|
| Identity | the persona `.md` files | filesystem (`~/.copilot/agents/`) |
| Per-agent long-term | teachAS learner-model, prepAS trackers, experimentAS ledger, coderAS kgraph | namespaced views over the shared substrate |
| Universal / shared | user prefs, project facts, cross-agent conventions | shared graph + KV (bridges Copilot `store_memory` + kgraph) |
| Working / episodic | current task's blackboard (artifacts) + run trace | event log |
| Semantic | retrieval across all of the above | vector index |

**Data-structure stack:** append-only **event log** (source of truth) → derived **knowledge
graph** (navigation: agents, tasks, artifacts, decisions, facts; edges `produced_by`,
`depends_on`, `supersedes`) + **vector index** (semantic recall) + **KV/relational** (fast
structured queries). This unifies the agents' currently heterogeneous stores under one
audited substrate while each agent keeps its own typed view.

## Storage & access
- **Substrate — local-first.** A single **SQLite** database holds the event log and the
  derived read models (`sqlite-vec` for embeddings). Zero-ops, transactional, portable,
  reproducible, and **no third-party data sharing**.
- **Access — MCP.** The orchestrator + memory are exposed as a **local SQLite-backed MCP
  server**, injected into every worker via `--additional-mcp-config`. MCP *is* the inter-agent
  facilitation protocol; the host CLI and all agents call memory/orchestration uniformly.
  (Consistent with the existing kgraph and seval MCP servers.)

## Security
- **Prompt-injection containment** — artifacts and tool results are untrusted *data*; the
  orchestrator mediates all cross-agent I/O and never lets one agent's output become another's
  instructions.
- **Secret hygiene** — secrets live in env/secret store, never in plans/artifacts/logs;
  `--secret-env-vars` redaction on every worker call.
- **Least privilege** — each worker gets only the directories/tools/URLs its node needs.

## Language & reuse
- Orchestrator in **Python** (the existing eval stack is Python; the agent-framework ecosystem
  for Backend C lives there).
- The DAG executor reuses the **`eval_platform` composable stage-runner pattern**
  (`core/pipeline/runner.py`: ordered execution, seam-contract validation, `--from`/`--to`
  slicing, `--resume`, `--max-workers`) generalized from a fixed 3-stage line to an arbitrary
  agent DAG.

## Future work
- **Backend C migration** — durable execution (LangGraph/Temporal) or the CLI `--acp` server.
- **Self-experimenting suite** — the plan *is* a pre-registration and the event log makes runs
  replayable, so managerAS + experimentAS can A/B alternative plans / agent configs and
  *measure* outcomes on real tasks. (Potential IP / paper novelty.)
- **Contract-typed routing** — treat agent I/O contracts as types and statically type-check a
  plan (reject impossible compositions before execution).
- **Reflection / critic loop** — optionally route artifacts through a verifier (rubber-duck /
  code-review) before acceptance. (managerAS applies a risk-based version of this today —
  see decision AS-011.)
- **patrecAS / learnAS — meta-learning module** — a standalone, researchable agent that learns
  the user's traits/demands/patterns and each agent's performance from the event log, and
  adapts agent behaviors. It maintains the **team/user model** that managerAS consumes for
  routing and realistic planning (decision AS-012). The contract between the two (model writer
  vs reader) is the integration seam.
