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
- **Phase:** 2 in progress + **Phase 4 done** + **Phase 5 nearly done** (resume + bounded
  parallelism). Memory: the event-sourced SQLite store + artifact persistence + run
  reconstruction are done and tested; the MCP access layer is the one remaining Phase 2 slice
  (deferred by owner). Phases 0–1 complete.
- **Built:** `agentsuite/` — `contracts/` (4 schemas + validator + models; `plan/v1` nodes
  support `inputs`, `depends_on`, `edges`, `approval`, `reversibility`, `budget`), `registry/`
  (loader) + 9 worker manifests, `runners/` (`AgentRunner`, `MockRunner`, `CopilotRunner`
  Backend A), `orchestrator/` (deterministic DAG executor: schema+registry validation,
  topo-order, seam validation, event trail with per-run `run_id`, storage-agnostic
  `event_sink`/`artifact_sink`, opt-in guardrails + approval gate, `resume_from` skip-completed,
  and a **bounded-parallel readiness scheduler** `max_workers` whose pool runs only `runner.run`),
  `memory/` (`MemoryStore` — append-only `event/v1` log + `(task_id,id)` artifacts, in-DB
  append-only triggers, `reconstruct` fold, schema-versioned), and `cli.py`
  (`run [--db] [--max-* guardrails] [--approve] [--resume] [--max-workers]` + `replay` —
  AS-013/014/015/016/017/018). `CopilotRunner` parses `--output-format json` and reports real
  usage (`cost.total_tokens`). Tests: **80 passing**.
- **Phase 2 exit (1/2):** a run persisted with `run --db` is fully reconstructable from the
  event log alone (`replay --task-id` folds events → identical status + artifacts).
- **Phase 4 (done):** opt-in caps (`max_total_tokens`/`max_wall_clock_s`/`max_nodes`/
  `max_agent_invocations`, all default unlimited) enforced by the orchestrator with structured
  `escalation{reason}`; approval-required nodes gate on an `approval_handler` and end `blocked`
  if unapproved. Verified end-to-end (AS-015).
- **Phase 5 (resume + parallelism done):** `run --db --resume` seeds the blackboard from
  persisted artifacts and skips completed nodes; per-run `run_id` keeps `event_id`s unique
  (AS-016). `--max-workers N` overlaps independent nodes via a readiness scheduler that offloads
  only `runner.run` to the pool (no locks); proven by a concurrency probe (peak==2 on two
  independent nodes, ==1 sequential) with guardrails/contracts intact (AS-017). Partial re-runs
  (`--from`/`--to`) remain.
- **De-risked (all retired):** Backend A invocation (R1), nested-CLI execution (R3) — live
  teachAS run; manager plan emission (R4) — live managerAS produced a valid 2-node `plan/v1`
  that the CLI executed in order with a full event trail. **Usage/cost (R2 partial):**
  `CopilotRunner` now parses `--output-format json` and reports `cost.total_tokens` (summed output
  tokens) — verified live, and a real run under `--max-tokens 1` trips `token_budget_exceeded` (AS-018).
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

### [AS-018] CopilotRunner reports usage — JSON output, summed output tokens
- **Status:** accepted.
- **Context:** the Phase 4 `max_total_tokens` guardrail accumulated `provenance.cost.total_tokens`,
  but Backend A ran with `-s` (text) and reported no usage, so the cap never bit on real runs.
- **Options considered:**
  - Keep `-s` text + estimate tokens from response length — pro: no output change; con: a fabricated
    number, not real usage; violates the provenance/"no magic numbers" bar.
  - **Switch to `--output-format json` (JSONL) and parse usage from the stream** — pro: real,
    CLI-reported figures; con: must fold a multi-line event stream into one artifact.
- **Decision:** `CopilotRunner` now invokes `copilot … --output-format json` and a pure
  `_parse_jsonl` folds the stream: the final answer is the last non-empty `assistant.message`
  content; **`outputTokens` are summed across all `assistant.message` events** and recorded as
  `provenance.cost.total_tokens` (a lower bound — the CLI exposes output tokens only). The `result`
  line's `usage` (premiumRequests, durations) and `sessionId`, plus the per-message `model`, are
  also captured. Parsing is robust to interleaved/non-JSON lines (skipped). Failure = process
  non-zero **or** `result.exitCode` non-zero.
- **Rationale:** gives the token guardrail a real signal with full provenance; keeps the artifact
  contract (`content.response`, `provenance.*`) unchanged for consumers (e.g. the smoke script).
- **Consequences:** verified live — a one-node teachAS run reported `cost.total_tokens=59`, and the
  same run under `--max-tokens 1` failed with `token_budget_exceeded` ("59 used"). Input/total
  tokens aren't exposed by the CLI, so the cap is a lower-bound ceiling; if exact accounting is
  needed later, source it from OpenTelemetry monitoring or a provider usage API.

### [AS-017] Bounded parallel execution — readiness scheduler, main-thread orchestration
- **Status:** accepted.
- **Context:** Phase 5 wants independent DAG nodes to run concurrently (`--max-workers`) without
  sacrificing the deterministic event log, seam validation, guardrails, or thread-safety.
- **Options considered:**
  - Level-by-level "wave" scheduling (barrier per topo level) — pro: simplest; con: a slow node
    in a level stalls independent ready nodes in the next level (suboptimal).
  - Full readiness scheduler with locks around shared state (blackboard/events/guardrails) — pro:
    maximal overlap; con: lock-heavy, easy to get wrong, hard to keep the log deterministic.
  - **Readiness scheduler where the thread pool runs *only* `runner.run`** — the main thread
    schedules ready nodes (deps resolved), submits the slow runner call to a `ThreadPoolExecutor`,
    and performs all gating/validation/persistence/guardrail accounting itself as futures complete.
- **Decision:** the third option. `Orchestrator(max_workers=N)`; `max_workers==1` keeps the exact
  sequential path (zero behaviour change). For `N>1`, `_run_parallel` submits ready nodes up to `N`
  and, as each future completes, runs `finalize` on the main thread. Because workers touch nothing
  but their own `runner.run`, **no shared state is concurrently mutated — no locks needed.**
  Approval prompts and pre-invoke guardrail reservations happen on the main thread before submit;
  on any failure, scheduling stops, in-flight workers drain, and the first failure is reported.
  CLI: `run --max-workers N`.
- **Rationale:** real overlap of independent nodes (proven by a concurrency-probe test: peak==2 on
  two independent nodes, ==1 at `max_workers=1`) with the single-threaded-orchestrator invariant
  intact, so the event log, contracts, and guardrails behave identically to the sequential path.
- **Consequences:** `runner` implementations must be safe to call concurrently (CopilotRunner is —
  stateless subprocess spawns). Event interleave across nodes is non-deterministic by nature, but
  per-node order and run reconstruction are unaffected. Partial re-runs (`--from`/`--to`) remain
  the last Phase 5 item.

### [AS-016] Resume from the event log — skip already-produced nodes
- **Status:** accepted.
- **Context:** Phase 5 wants an interrupted multi-node run to be resumable. The Phase 2 store
  already persists every artifact by `(task_id, id)`. How should resume decide what to skip, and
  how do repeated runs of the same `task_id` avoid `event_id` collisions?
- **Options considered:**
  - Replay the event log to compute completed nodes — pro: pure event-sourcing; con: more code,
    must reconcile partial/failed events.
  - **Seed the blackboard from persisted artifacts; skip any node whose `produces` is present** —
    pro: trivial, deterministic, idempotent (failed artifacts are never persisted, so only truly
    completed nodes are skipped); con: relies on the artifacts table as the completion truth.
- **Decision:** `Orchestrator.run(plan, resume_from=...)` seeds the blackboard with the supplied
  artifacts; a node whose `produces` is already present is skipped with a `node_completed`
  `{skipped: "resumed"}` event (no runner call, no budget spend, no approval re-prompt). CLI
  `run --db PATH --resume` loads `store.artifacts_for(task_id)` as the seed (requires `--db`).
  Each `run` now stamps a per-invocation `run_id` (uuid) into every `event_id`
  (`{task_id}-{run_id}-{n}`) so a resumed run's events never collide with the prior run's under
  the store's `UNIQUE(event_id)` constraint.
- **Rationale:** reuses the persisted blackboard as the source of completion truth; failed nodes
  aren't persisted so they correctly re-run; `run_id` keeps the append-only log unambiguous across
  multiple runs of one task.
- **Consequences:** partial re-runs (`--from`/`--to`) and bounded parallelism (`--max-workers`)
  remain the rest of Phase 5. A node's output is considered done purely by artifact presence; if a
  future need arises to force re-execution, add an explicit `--force`/node selector.

### [AS-015] Phase 4 guardrails — orchestrator-enforced, opt-in caps + approval gate
- **Status:** accepted.
- **Context:** before billable multi-node runs, the orchestrator needs budget/timeout/loop caps
  and a human-in-the-loop approval gate (AS-005). Where do limits live, and what are the defaults?
- **Options considered:**
  - Per-agent guardrails inside each worker — pro: local; con: not enforceable centrally,
    duplicated, agents are untrusted to self-limit. Rejected (violates AS-005).
  - Hard-coded default caps in the orchestrator — pro: safe-by-default; con: violates the
    "no hard-coded pass/fail thresholds" principle; surprises the owner.
  - **Configurable `Guardrails` the orchestrator enforces, every limit defaulting to `None`
    (unlimited)** — opt-in per run; deterministic; reported via events on breach.
- **Decision:** `agentsuite/orchestrator/guardrails.py` — a frozen `Guardrails(max_total_tokens,
  max_wall_clock_s, max_nodes, max_agent_invocations)` (all `None` = no cap) + a `GuardrailState`
  the orchestrator checks **before** each node (deadline / node-count / per-agent invocation —
  the loop guard) and **after** each node (token accounting from `provenance.cost.total_tokens`,
  best-effort: absent usage counts as 0). A breach emits `node_failed` + `escalation{reason}` and
  ends the run `failed`. The **approval gate**: a node with `approval: required` emits
  `approval_requested`, consults an `approval_handler(node) -> bool`; granted → `approval_granted`
  and proceed; denied or no handler → `escalation{approval_denied|approval_required}` and the run
  ends **`blocked`** (new status) without executing the node. CLI: `run --max-tokens/--max-seconds/
  --max-nodes/--max-agent-calls`, and `--approve` (auto) else an interactive prompt (denies when
  not a TTY).
- **Rationale:** centralizes enforcement (AS-005), keeps the executor deterministic, honors
  "configurable not hard-coded" + "stop-and-confirm on one-way doors" (irreversible nodes gate on
  approval), and the escalation reasons give the manager a structured signal to re-plan.
- **Consequences:** real token enforcement needs the runner to report usage (CopilotRunner does
  not yet — Backend A uses `-s` text); the cap is a working ceiling now and exact once usage lands.
  Manager-side re-planning consumes the `escalation` events; `blocked` is distinct from `failed`.

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

## 7. Next actions (immediate)
1. ✅ SQLite schema + append-only `event/v1` writer; `event_sink`/`artifact_sink` wired so every
   run is durably reconstructable (AS-006/007/014). `MemoryStore` + `replay` CLI.
2. ✅ Artifacts (blackboard) persisted + resolvable by id (`get_artifact`, `artifacts_for`).
3. ✅ **Phase 4 guardrails pulled forward** — opt-in budget/timeout/node/agent caps + approval
   gate, orchestrator-enforced with structured escalation (AS-015).
4. ✅ **Phase 5 `--resume` + bounded parallelism** — `run --db --resume` skips already-completed
   nodes (AS-016); `run --max-workers N` overlaps independent nodes via a no-lock readiness
   scheduler (AS-017). Partial re-runs (`--from`/`--to`) remain.
5. ⏭ **Phase 2 MCP slice (deferred):** local MCP server exposing memory read/write; inject into
   workers via `--additional-mcp-config`. Decision pending — framework/shape + the dependency it
   adds (AS-014 consequences). Owner deferred in favour of guardrails.
6. ✅ **Real usage/cost** — `CopilotRunner` parses `--output-format json` and reports
   `cost.total_tokens`; the `max_total_tokens` guardrail now bites on real runs (AS-018).
7. **Next candidates:** (a) Phase 5 finish — partial re-runs (`--from`/`--to`) + a live multi-agent
   end-to-end run; (b) the deferred memory MCP slice; (c) result caching keyed on the provenance
   hash (handoff §4). Refresh the kgraph map alongside.

## 8. Related precedents (reuse, don't reinvent)
- `eval_platform/core/pipeline/runner.py` — composable stage runner (the orchestrator skeleton).
- `eval_platform` versioned JSON contracts + domain-agnostic "ship mechanism, not data" principle.
- `kgraph` — graph memory + MCP server (extend to suite scope for AS-006/AS-007).
- The `AS`-convention agent personas in `~/.copilot/agents/` (the workers).
