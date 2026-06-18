# AgentSuite — Handoff

> Current state + next actions for the AgentSuite orchestration project. Rationale lives in
> the decision log below; `architecture.md` is the normative target spec; `plan.md` is the
> phased build order.

## 1. What this is
A manager-orchestrated multi-agent system over the user's existing `AS` agent suite
(coderAS, experimentAS, teachAS, prepAS, researchAS, paperAS, patentAS, presentAS, discussAS).
**managerAS** is the only user-facing agent: it turns a task (structured or vague) into a
typed, validated **plan (DAG)**; a **deterministic Python orchestrator** executes that plan by
invoking worker agents as **headless `copilot` processes** and routing typed **artifacts**
between them through a **local SQLite + MCP** memory substrate.

## 2. Current state
- **Phase:** 1 (MVP vertical slice) — **runs end-to-end**. Phase 0 complete.
- **Built:** `agentsuite/` package — `contracts/` (4 JSON Schemas + validator + dataclass
  models), `registry/` (manifest loader) + 9 worker manifests in `registry/`, `runners/`
  (`AgentRunner` interface, `MockRunner`, `CopilotRunner` Backend A), `orchestrator/`
  (deterministic DAG executor: schema+registry validation, topo-order, seam validation,
  event trail). Tests: **30 passing**. `scripts/smoke_backend_a.py` proves a live run.
- **De-risked:** Backend A invocation (R1) and nested-CLI execution (R3) both retired by a
  real run — teachAS answered headlessly and the orchestrator validated the seam.
- **managerAS authored:** `~/.copilot/agents/managerAS.md` (user-agnostic; three layers).
- **Remaining for Phase 1:** auto-ingest a plan emitted by managerAS into `Orchestrator.run`.

## 3. Reliability (design intent)
- **Determinism where it counts:** the orchestrator's control flow is deterministic code;
  LLM judgment is confined to the manager and to explicitly-defined escalation points.
- **Seam-contract validation:** every artifact is validated against its declared type before a
  downstream node consumes it (the `eval_platform` entry-seam rule).
- **Replay & audit:** append-only event log is the source of truth; any run is reconstructable.
- **Resumability:** `--resume` skips completed nodes; `--from`/`--to` re-run sub-graphs.
- **Guardrails:** budget/token caps, timeouts, max delegation depth, loop detection, approval
  gates — all orchestrator-enforced, not per-agent.

## 4. Optimizations (planned)
- Bounded parallel workers over independent DAG nodes (`--max-workers`).
- Artifact referencing **by id** (not inline copy) to avoid context bloat.
- LLM/result caching keyed on (agent, prompt, inputs) provenance hash.
- Semantic retrieval (vector) so the manager pulls only relevant prior context.

## 5. Decision log (ADR-style)
> Append-only. Stable anchors; when superseded, keep the anchor and change the title.

### [AS-001] Orchestrator-workers + blackboard pattern
- **Status:** accepted.
- **Decision:** manager = LLM planner/router/aggregator (only user-facing); deterministic
  orchestrator = mechanism; workers communicate only through a typed-artifact blackboard.
- **Rationale:** isolates non-determinism to the manager; reproducible, auditable, testable;
  matches proven orchestrator-worker / plan-and-execute patterns.

### [AS-002] Plan is a typed, versioned DAG — not a flat list
- **Status:** accepted.
- **Decision:** `plan/v1` = nodes + `depends_on` edges + inputs/outputs referenced by artifact
  id; validated against schema *and* capability registry before execution.
- **Rationale:** captures dependencies, parallelism, and data flow; preserves provenance;
  avoids context bloat.

### [AS-003] Agents talk through the blackboard; artifacts are untrusted data
- **Status:** accepted.
- **Decision:** no direct agent↔agent chat; the orchestrator mediates all I/O; an upstream
  artifact is untrusted input to a downstream agent (prompt-injection containment).

### [AS-004] Capability registry drives routing
- **Status:** accepted.
- **Decision:** machine-readable `registry/v1` manifest per agent; manager routes by matching
  task requirements to agent contracts; adding an agent = adding a manifest.

### [AS-005] Orchestrator-level guardrails
- **Status:** accepted.
- **Decision:** budget caps, timeouts, max depth, loop detection, and human-in-the-loop
  approval gates live in the orchestrator, not in individual agents.

### [AS-006] Layered memory on a CQRS substrate
- **Status:** accepted.
- **Decision:** append-only event log (source of truth) → derived knowledge graph + vector
  index + KV (read models). Layers: identity / per-agent / universal / working / semantic.
- **Rationale:** unifies the agents' heterogeneous stores under one audited substrate while
  keeping per-agent typed views; gives replay and provenance for free.

### [AS-007] Local-first SQLite, MCP access layer
- **Status:** accepted.
- **Decision:** single SQLite DB (event log + read models, `sqlite-vec`); exposed as a local
  MCP server injected into every worker via `--additional-mcp-config`.
- **Rationale:** "MCP vs local" is orthogonal — local substrate + MCP access gives zero-ops,
  reproducible, no-3P-sharing storage with uniform tool access. Matches kgraph/seval MCP usage.

### [AS-008] Python orchestrator, reusing the eval_platform stage-runner
- **Status:** accepted.
- **Decision:** Python; generalize `eval_platform`'s composable stage runner (ordered exec,
  seam validation, `--resume`, `--max-workers`) from a fixed 3-stage line to an arbitrary DAG.

### [AS-009] Swappable AgentRunner — Backend A now, Backend C later
- **Status:** accepted.
- **Decision:** `AgentRunner.run(...)` interface; **Backend A** = headless `copilot --agent X
  -p … --output-format json`; **Backend C** (LangGraph/durable or `--acp`) scoped for a planned
  migration. Plan/memory/registry stay invocation-agnostic. (Backend B, in-CLI Task tool, not
  pursued.)
- **Rationale:** reuses existing `.md` personas verbatim, real determinism, stays in the
  Copilot ecosystem; the seam keeps the C migration cheap.

### [AS-010] The suite as a reproducible, self-experimenting system
- **Status:** proposed (future).
- **Decision:** treat the plan as a pre-registration and the event log as replay, enabling
  managerAS + experimentAS to A/B alternative plans/configs and measure outcomes.
- **Rationale:** genuine novelty; potential IP/paper (cf. eval_platform patent-disclosure).

### [AS-011] managerAS behavioral policy
- **Status:** accepted.
- **Decision:** managerAS (the only user-facing agent) acts like an experienced CEO/quality
  manager. Policy: **consultative intake** — clarify the mission thoroughly with the user
  before committing to a plan; **risk-based quality gate** — verify each worker artifact
  against the node's success criteria and route high-stakes/irreversible outputs through a
  critic (rubber-duck / code-review / the relevant AS critic) before accepting, with lighter
  checks on low-stakes nodes; **consumes a team/user model** to route and plan realistically.
- **Rationale:** fewer wrong turns on vague tasks; CEO accountability for the result; learns
  the team over time. Leadership persona layer sits on top of the AS-001..009 mechanism.

### [AS-012] patrecAS / learnAS — meta-learning module (future, standalone novelty)
- **Status:** proposed (future, separate research module).
- **Decision:** a dedicated agent/module, **patrecAS/learnAS**, learns the user's traits,
  demands, and patterns and each agent's performance, and adapts agent behaviors accordingly.
  managerAS (and the suite) *consume* the team/user model it maintains; managerAS does **not**
  own this learning. Until it exists, managerAS keeps only a lightweight team-performance
  record.
- **Rationale:** keeps managerAS focused on orchestration+leadership; the adaptive learning
  layer is a researchable novelty in its own right (personalization + agent-behavior adaptation
  over the event-log substrate).
- **Consequences:** define the team/user-model contract as the seam between patrecAS/learnAS
  (writer) and managerAS (reader); it reads from the AS-006 event log.

## 6. Open questions / next decisions
- **Q1 — Plan schema depth:** finalize `plan/v1` fields (retry policy, conditional edges `on:
  success|failure`, fan-out/fan-in). *Next decision before Phase 0 schemas.*
- **Q2 — managerAS authoring:** is managerAS a Copilot custom agent (`.md`) like the others, or
  a thin code+LLM component? (Leaning: `.md` persona constrained to emit `plan/v1` JSON.)
- **Q3 — Memory unification:** migrate existing per-agent stores (teachAS/prepAS/experimentAS/
  kgraph) into the substrate now, or bridge them lazily? (Leaning: bridge lazily.)
- **Q4 — Nested-CLI isolation:** confirm headless `copilot` workers run cleanly from a parent
  session (workspace, session-id, env). *Retire early in Phase 1 (risk R3).*
- **Q5 — Repo hygiene:** initialize git + `.gitignore` (exclude SQLite DB, run outputs, caches).

## 7. Next actions (immediate)
1. Initialize git + `pyproject.toml` + `.gitignore` for `C:\Code\AgentSuite\`.
2. Author the four JSON Schemas (`plan/v1`, `artifact/v1`, `registry/v1`, `event/v1`) + validators + tests (Phase 0).
3. Write capability manifests for the existing AS agents in `registry/`.
4. ~~Draft the **managerAS** persona~~ — **done**: `~/.copilot/agents/managerAS.md` (user-agnostic; three layers — JARVIS temperament / CEO methodology / AgentSuite mechanism; resolves Q2 toward a constrained `.md` persona that emits `plan/v1`).
5. Spike Backend A: a Python `AgentRunner` that spawns one worker and parses JSONL → `artifact/v1` (retires R3), then wire the Phase-1 single-node slice.
6. Initialize a kgraph project for AgentSuite and seed nodes from `architecture.md`.

## 8. Related precedents (reuse, don't reinvent)
- `eval_platform/core/pipeline/runner.py` — composable stage runner (the orchestrator skeleton).
- `eval_platform` versioned JSON contracts + domain-agnostic "ship mechanism, not data" principle.
- `kgraph` — graph memory + MCP server (extend to suite scope for AS-006/AS-007).
- The `AS`-convention agent personas in `~/.copilot/agents/` (the workers).
