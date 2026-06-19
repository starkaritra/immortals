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
- **Phase:** 2 **in progress** — memory substrate: the event-sourced SQLite store + artifact
  persistence + run reconstruction are done and tested; the MCP access layer is the remaining
  Phase 2 slice. Phases 0–1 complete.
- **Built:** `agentsuite/` — `contracts/` (4 schemas + validator + models; `plan/v1` nodes
  support `inputs`, `depends_on`, and `edges` for dependencies), `registry/` (loader) + 9
  worker manifests, `runners/` (`AgentRunner`, `MockRunner`, `CopilotRunner` Backend A),
  `orchestrator/` (deterministic DAG executor with schema+registry validation, topo-order,
  seam validation, event trail; writes through storage-agnostic `event_sink`/`artifact_sink`),
  `memory/` (`MemoryStore` — append-only `event/v1` log + `(task_id,id)` artifacts, in-DB
  append-only triggers, `reconstruct` fold, schema-versioned), and `cli.py`
  (`python -m agentsuite run [--db PATH]` + `python -m agentsuite replay` — decisions AS-013/014).
  Tests: **50 passing**.
- **Phase 2 exit (1/2):** a run persisted with `run --db` is fully reconstructable from the
  event log alone (`replay --task-id` folds events → identical status + artifacts). Verified
  end-to-end on a 2-node mock DAG.
- **De-risked (all retired):** Backend A invocation (R1), nested-CLI execution (R3) — live
  teachAS run; manager plan emission (R4) — live managerAS produced a valid 2-node `plan/v1`
  that the CLI executed in order with a full event trail.
- **managerAS authored & wired:** `~/.copilot/agents/managerAS.md` (user-agnostic; three
  layers; execution model = "managerAS in the loop", invokes the CLI seam).
- **Topology settled (AS-013):** manager is the interactive driver; orchestrator is a tool it
  calls; only workers run headless.

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

### [AS-014] Memory store — event-sourced SQLite, wired via storage-agnostic sinks
- **Status:** accepted.
- **Context:** Phase 2 needs durable, reconstructable runs (AS-006/007). How should the
  orchestrator persist its event log + artifacts without coupling the deterministic executor to
  a storage engine?
- **Options considered:**
  - Orchestrator owns a `MemoryStore` directly — pro: less wiring; con: couples execution to
    SQLite, harder to test, violates DIP.
  - Storage-agnostic callback **sinks** (`event_sink`, `artifact_sink`) the store satisfies —
    pro: orchestrator stays storage-free, in-memory runs unchanged, store is independently
    testable; con: two seams to wire at the call site (CLI).
- **Decision:** `agentsuite/memory/store.py` `MemoryStore` over local SQLite — an **append-only
  `events` table** (source of truth) + an `artifacts` table keyed by `(task_id, id)`. The
  orchestrator writes through `event_sink`/`artifact_sink` callbacks only; persistence is opt-in
  (`run --db PATH`). A run reconstructs by **folding the event log** (`reconstruct` / `replay`
  CLI). Append-only is enforced in-DB by `RAISE(ABORT)` triggers on UPDATE/DELETE of `events`;
  `event_id` is unique so replays are idempotent.
- **Rationale:** confines storage behind a contract seam (DIP/SOLID), keeps the executor
  deterministic and storage-free, makes "a run is reconstructable from the log" a tested
  property, and leaves room for derived read models (graph/vector, Phase 6) over the same log.
- **Consequences:** schema is versioned via `PRAGMA user_version` (migration guard). The **MCP
  access layer** (exposing this store to workers via `--additional-mcp-config`) is the remaining
  Phase 2 slice — its framework/shape is the next decision (adds a dependency; needs sign-off).

### [AS-013] Execution topology — "managerAS in the loop"
- **Status:** accepted.
- **Context:** managerAS must do consultative intake (talk to the user) and is the only
  user-facing agent, but the orchestrator drives workers headlessly (`--no-ask-user`). How do
  human-in-the-loop intake and a headless orchestrator coexist?
- **Decision:** **managerAS is always the interactive, foreground driver** — it does intake
  (with `ask_user`) and final synthesis with the user, emits a `plan/v1`, and **invokes the
  deterministic orchestrator as a tool** (MVP: `shell` → `python -m agentsuite run --plan-file
  …`; production: the orchestrator MCP server). **Only worker agents run headless**, spawned by
  the orchestrator. managerAS is never the headless one on the normal path.
- **Consequences:** a headless managerAS (no intake, autonomous assumptions) is kept as a
  **future automation mode** for self-experimentation / patrecAS-driven runs, reusing the same
  `python -m agentsuite run` seam. Build target: a CLI `run` command + managerAS wired to call
  it. Resolves open question Q2.

## 6. Open questions / next decisions
- **Q1 — Plan schema depth (partial):** `inputs`/`depends_on`/`edges` done. Still open: retry
  policy and conditional edges (`on: success|failure` branching is in the schema but the
  executor treats edges as ordering only — failure currently stops the run). Revisit in Phase 4/5.
- **Q3 — Memory unification:** migrate existing per-agent stores (teachAS/prepAS/experimentAS/
  kgraph) into the substrate now, or bridge them lazily? (Leaning: bridge lazily.) *Phase 2/6.*
- **Q6 — Synthesis pass:** should the CLI offer a `synthesize` helper, or does managerAS always
  synthesize from the returned artifacts itself? (Leaning: manager synthesizes; CLI stays
  execution-only.)
- *(Resolved: Q2 managerAS authoring → `.md` persona, AS-013; Q4 nested-CLI → R3 retired;
  Q5 repo hygiene → git initialized, `.gitignore` in place.)*

## 7. Next actions (immediate) — Phase 2: memory substrate
1. ✅ SQLite schema + append-only `event/v1` writer; orchestrator's `event_sink`/`artifact_sink`
   wired so every run is durably reconstructable (AS-006/007/014). `MemoryStore` + `replay` CLI.
2. ✅ Artifacts (blackboard) persisted + resolvable by id (`get_artifact`, `artifacts_for`).
3. ⏭ Local **MCP server** exposing memory read/write; inject into workers via
   `--additional-mcp-config` so agents share memory. **Next decision** — framework/shape +
   the dependency it adds (needs sign-off; AS-014 consequences).
4. Then **Phase 4 (pull forward): guardrails** — budget/token caps, timeouts, approval gates —
   before unleashing multi-node *real* (billable) runs.
5. Initialize a kgraph project for AgentSuite and seed nodes from `architecture.md`.

## 8. Related precedents (reuse, don't reinvent)
- `eval_platform/core/pipeline/runner.py` — composable stage runner (the orchestrator skeleton).
- `eval_platform` versioned JSON contracts + domain-agnostic "ship mechanism, not data" principle.
- `kgraph` — graph memory + MCP server (extend to suite scope for AS-006/AS-007).
- The `AS`-convention agent personas in `~/.copilot/agents/` (the workers).
