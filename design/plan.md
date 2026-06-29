# Immortals — Plan

Build order favors a **thin vertical slice that runs end-to-end first**, then deepens each
component. Every phase ends with something runnable and a measured result, not broad stubs.

## Phase 0 — Scaffold & contracts (foundation)
- [x] Decide architecture, invocation backend, storage (see `handoff.md` decision log).
- [x] Verify Backend A feasibility (`copilot --agent X -p … --output-format json`).
- [x] Create the Python package skeleton (`immortals/`), `pyproject.toml`, test harness, `.gitignore`.
- [x] Author the JSON Schemas: `plan/v1`, `artifact/v1`, `registry/v1`, `event/v1` + validators + dataclass models.
- [x] Write capability manifests (`registry/<agent>.json`) for the existing AS agents (9 workers).
- **Exit:** ✅ schemas validate sample plans/artifacts; `pytest` green (30 passed).

## Phase 1 — MVP vertical slice (single agent, end-to-end)
- [x] `AgentRunner` interface + **Backend A** implementation (spawn `copilot`, `-s` text → `artifact/v1`). MockRunner for tests.
- [x] Minimal orchestrator: validate plan (schema + registry) → topo-order → invoke via runner → validate seam → aggregate, with event trail.
- [x] **Backend A retired risk R3**: live one-node run (teachAS) succeeded end-to-end via `scripts/smoke_backend_a.py`.
- [x] managerAS persona (planner) authored at `~/.copilot/agents/managerAS.md`; emits `plan/v1`.
- [x] Glue: CLI `python -m immortals run --plan-file …` (the orchestrator seam, decision AS-013); managerAS invokes it via shell and synthesizes. `depends_on` made first-class after observing managerAS's natural output.
- **Exit:** ✅ **Phase 1 done.** A live managerAS planning call emitted a valid 2-node `plan/v1`; the CLI executed it in dependency order with a full event trail. Backend A proven on a real worker run.

## Phase 2 — Memory substrate (event log + MCP)
- [x] SQLite schema: `events` (append-only, in-DB triggers) + `artifacts` + `notes` KV (schema v2).
- [x] Event-sourcing writer via storage-agnostic `event_sink`/`artifact_sink` (`MemoryStore`, AS-014);
  `run --db` + `replay` CLI.
- [x] Local **MCP server** (`immortals/memory/mcp_server.py`, zero-dep stdio JSON-RPC) exposing
  artifact/event reads + a shared `notes` KV; injected via `run --share-memory`
  (`--additional-mcp-config` + `IMMORTALS_MEMORY_DB` env). Server verified live (default agent
  wrote a note); **custom-agent exposure needs a one-time persistent `copilot mcp add`** — a CLI
  constraint, not a code gap (AS-021).
- [x] Blackboard: artifacts persisted + resolvable by id across nodes/runs.
- **Exit:** ✅ a run is fully reconstructable from the event log; ✅ the memory MCP server works
  (default agent live); ⏭ custom-agent worker sharing pends the documented persistent registration.

## Phase 3 — Routing & registry — DONE
- [x] Registry-driven routing: `Registry.route(need)` ranks manifests deterministically; CLI
  `agents` (catalogue) + `route --need` (ranked candidates) — managerAS routes with no hardcoding (AS-020).
- [x] Registry approval floor (opt-in): `--enforce-approvals` makes a manifest's `approval_default`
  a sign-off floor (a node may raise, not lower) — registering a high-stakes agent auto-gates it.
- [~] Static artifact-type checking (`produces`/`consumes`) deferred — plans carry ids not types and
  runners emit a generic type today; needs typed plan nodes or semantic runner output (AS-020).
- **Exit:** ✅ adding an agent = adding a manifest; the manager picks it via `route`/`agents` with no
  orchestrator change; the manifest's approval policy applies automatically under enforcement.

## Phase 4 — Guardrails & human-in-the-loop
- [x] Budget/token caps, timeouts, max node executions, per-agent invocation cap (loop guard) —
  opt-in `Guardrails` (default unlimited), orchestrator-enforced, structured escalation (AS-015).
- [x] Approval gates (`approval: required`) — orchestrator emits `approval_requested`, consults an
  `approval_handler`, and ends the run `blocked` if unapproved; CLI `--approve` / interactive prompt.
- [x] Escalation path: failure / contract violation / guardrail breach → `node_failed` +
  `escalation{reason}`, returned to the manager (re-plan is manager-side).
- **Exit:** ✅ a capped run halts with the breach reason; an approval-gated node waits for sign-off
  (blocks without it). Note: token cap bites once a runner reports usage (`provenance.cost`).

## Phase 5 — Multi-agent DAG (parallelism, resume) — DONE
- [x] Topological readiness scheduler with bounded parallel workers (`--max-workers`); the pool
  runs only `runner.run` while the main thread owns all state — no locks (AS-017).
- [x] `--resume` from the event log (skip completed nodes via the persisted blackboard, AS-016);
  per-run `run_id` keeps `event_id`s unique across re-runs.
- [x] Partial re-runs (`--from`/`--to`): execute the descendants-of-from ∩ ancestors-of-to slice,
  force-run it, source the rest from the store (AS-019).
- [x] End-to-end multi-agent task — live: experimentAS designs a tiny experiment → teachAS explains
  it from the upstream artifact; status completed, data flow + token usage + event log verified,
  run reconstructable via `replay`.
- **Exit:** ✅ a 3+ node DAG runs with parallelism, is resumable after an interrupt, supports
  partial re-runs, and a real 2-agent run completed end-to-end.

## Phase 6 — Derived memory (graph + vector) — DONE
- [x] Project events/artifacts/facts into a knowledge graph (`DerivedMemory.graph/neighbors`):
  nodes task/agent/artifact/fact; edges `produced_by`/`contains`/`depends_on`/`supersedes` (AS-023).
- [x] Pluggable `Embedder` seam + zero-dep deterministic default (unsigned hashed BoW); vector index
  over artifacts + facts; semantic `search()` for the manager's context. `sqlite-vec` + a real model
  is the named future backend behind the seam, not the MVP (AS-023).
- [x] Agent-namespaced `facts` (with `source` provenance + `supersedes`) + per-agent/per-task scoped
  views over the shared substrate; MCP (`memory_search`/`memory_graph`/`memory_add_fact`/
  `memory_list_facts`) + `immortals recall` CLI.
- **Exit:** ✅ manager retrieves relevant prior artifacts/facts semantically (`recall --query`); graph
  navigable (`recall --graph`). Verified live over a real run; 22 tests.

## Vision roadmap (Phases 6.5–10) — "a team you delegate to" (AS-029)
> The Phase 0–6 engine is the substrate. These phases build the north star on top: hand it a task →
> a long-running agent (minutes→days) drives to a tangible outcome → it pings you only when it
> truly needs you → it earns autonomy as it learns you. Each phase still ends with something
> runnable.
>
> **Beachhead (AS-029 stress-test):** start with a **small set of externally-verifiable, code-shaped
> tasks** (the domain the `innovation-digest` run already proved), then scale to judgment-quality
> tasks later. **Build order: eval-first (6.5) → durable lifecycle (7) → service (8) → check-in
> policy (9) → surface + autonomy (10),** with the **Backend-C gate resolved before 7–8**.

### Phase 6.5 — Outcome-quality eval harness (PREREQUISITE, AS-029 keystone)
> Moved ahead of Phase 7 by the red-team: you cannot tune the Phase-9 threshold, bound Phase-10
> autonomy, or detect days-scale drift without a ground-truth quality signal.
- [ ] **Instrumented probe run:** one deliberately larger, **externally-verifiable** task
  (~10–15 nodes, multi-hour) through the *existing* engine; log (a) every silent assumption, (b)
  where a check-in would have saved it, (c) whether the deliverable is externally correct.
- [ ] **Outcome metric:** "did the external check pass?" (tests *not* authored by the agent, a real
  deploy/run, a benchmark, a checkable fact) — the beachhead's ground truth.
- [ ] **Derive the Phase-9 check-in taxonomy from the observed failures** (evidence, not speculation).
- **Exit:** a repeatable run that scores outcome quality on a verifiable task + a first, evidence-
  based catalogue of when a human checkpoint actually mattered.
- ✅ **Tooling in place:** the read-only `immortals dashboard` (see `prototype-frontend-handoff.md`)
  is the inspection surface for this probe — visualizes runs, the DAG, artifacts, the event
  timeline, and recall over the event store.

### Phase 7 — Durable task lifecycle (keystone) — ⚠ resolve the Backend-C gate (R10) first
- [ ] **Decide bespoke-vs-adopt** (R10): hand-built durable lifecycle vs LangGraph/Temporal as
  Backend C (AS-009). One-way door — settle before building below.
- [ ] **Tasks as first-class durable entities**: a `tasks` layer over the event store
  (`task_id`, `goal`, `status`, timestamps), states `queued → planning → running →
  waiting_on_human → blocked → completed → failed`; reconstructable like everything else.
- [ ] **Async human-in-the-loop**: generalize the synchronous approval gate (AS-015) to **park &
  resume** — a task persists a `waiting_on_human` state, releases the process, and continues when
  the owner answers (so a task can wait hours/days without holding anything open).
- [ ] **Durable resume across restarts**: on startup, load in-flight tasks and advance the runnable
  ones (reuses the `--resume`/event-log spine, AS-016).
- **Exit:** a task survives a process kill + restart mid-run, parks for human input, and resumes to
  completion from the event log; minutes-scale and (simulated) days-scale both work.

### Phase 8 — manager-as-a-service (the always-on daemon) — AS-025
> ✅ **Read-half started:** the `immortals dashboard` FastAPI app already exposes the read endpoints
> (`GET /api/runs`, `/runs/{id}`, `/runs/{id}/graph`, `/artifacts/…`, `/recall`) — this phase adds
> the write/stream half (`POST /tasks`, WebSocket) additively onto the same app.
- [ ] Small local service (FastAPI, bound `127.0.0.1` + token) hosting the Phase-7 lifecycle.
- [ ] Versioned **streaming API (WebSocket)**: submit a task, stream progress, deliver check-in
  requests, accept answers, return the final outcome — all async.
- [ ] Manager driver behind it (shell `managerAS -p` per turn **or** a thin Python manager — open Q).
- **Exit:** submit a task to the running daemon, close the client, reconnect later, and retrieve the
  in-progress/finished state; a parked check-in is delivered and answerable over the API.

### Phase 9 — Calibrated check-in policy ★ (the novel/IP core) — DECIDE engine
> Reframed by the AS-029 stress-test: the goal is **calibrated uncertainty checkpointing**, *not*
> ping-minimization. Anti-spam is a budget on top. Signals must be **verifiability-agnostic** (R-F)
> so the policy transfers from the verifiable beachhead to judgment-quality tasks later.
- [ ] **Trigger taxonomy** (derived from the Phase-6.5 probe, not guessed): classify when a running
  task may interrupt — `needs_clarification`, `needs_decision`, `needs_approval` (exists),
  `milestone`/`done` — scored by **verifiability-agnostic uncertainty** (agent confidence, plan
  ambiguity, decision irreversibility, novelty-vs-memory).
- [ ] **Calibration over suppression**: tune to right-sized checkpointing (guard against silent
  under-asking → confidently-wrong deliverables), *then* apply the budget.
- [ ] **Notification budget**: per-day/quiet-hours rate limit + de-duplication — the anti-Swiggy
  guardrail; a low-importance trigger is suppressed or batched, not sent.
- [ ] **Provenance**: every check-in (and every *suppressed* one) records why it fired/was held —
  the labelled signal the Phase-10 learning loop calibrates against.
- **Exit:** on a multi-step task, genuine forks/milestones surface and silent wrong-assumptions are
  caught; noise stays under budget; each ping carries its justification; suppressed triggers are
  logged for calibration.

### Phase 10 — Conversational surface + earned autonomy — AS-026 / AS-027
> ✅ **Concept mockup shipped:** `prototype/jarvis-bubble/` is a standalone scripted demo of the
> intended desktop-bubble experience (PM/Applied-DS/SWE personas; delegate → silent work → one
> calibrated ping → verified provenance-stamped report). Not wired — it de-risks the UX and is a
> shareable artifact for the vision, ahead of the real Tauri build.
- [ ] Tauri floating-bubble client (AS-026) — a thin client over the Phase-8 API (text first; voice
  STT/TTS optional later).
- [ ] **patrecAS/learnAS** (AS-027): learn the owner's accept/dismiss patterns → tune the Phase-9
  threshold and **graduate autonomy** on low-risk actions (propose-not-apply remains the floor).
- **Exit:** the check-in threshold demonstrably adapts to the owner's feedback; a low-risk action
  the owner has repeatedly accepted is (reversibly, audibly) auto-handled.

### Supporting / inventive (parallel to 7–10, not the headline)
- [ ] **Backend C** migration (LangGraph/durable or `--acp`) behind the same `AgentRunner`.
- [ ] **Self-experimenting suite**: A/B alternative plans / agent configs, measured via the event log.
- [ ] **Contract-typed routing**: static type-check of plan composition (the deferred AS-020 item).
- [ ] Reflection/critic loop before artifact acceptance.

## Milestone map
| Milestone | Phases | Demonstrable outcome |
|---|---|---|
| M1 — "It runs" | 0–1 | Manager → orchestrator → one headless worker → answer |
| M2 — "It remembers" | 2–3 | Event-sourced, MCP-shared memory; registry-routed |
| M3 — "It's safe & parallel" | 4–5 | Guardrails, approval gates, resumable multi-agent DAG |
| M4 — "It learns & migrates" | 6 | Semantic memory; Backend C path; self-experimentation |
| **M5 — "It's a team you delegate to"** | **6.5–10** | **Delegate a goal → walk away → a long-running agent returns finished work, pinging you only when it matters, earning autonomy (AS-029). Gated on an outcome-quality eval (6.5) and the Backend-C decision (R10).** |

## Risk & assumption register
| # | Risk / assumption | Status | Mitigation |
|---|---|---|---|
| R1 | Backend A can run a named agent headlessly & return parseable output | **Retired** | Verified: `--agent`, `-p`, `--output-format json`, `--no-ask-user`, `--allow-all-tools` |
| R2 | Headless worker latency/cost is acceptable for multi-node DAGs | **Mitigating** | Usage now measured per run (`cost.total_tokens`/durations from `--output-format json`, AS-018); budget caps + parallelism in place; caching next |
| R3 | Nested `copilot` invocation (CLI-in-CLI) behaves cleanly | **Retired** | Live smoke test: `scripts/smoke_backend_a.py` ran teachAS headless end-to-end, valid artifact returned |
| R4 | Manager reliably emits schema-valid plans | **Retired** | Live managerAS planning call emitted a valid 2-node `plan/v1`; `depends_on` made first-class to match its natural output; reject-and-retry still available |
| R5 | Memory-poisoning / stale facts across runs | Open | Provenance on every fact; supersede edges; injection containment |
| R6 | Backend C migration stays cheap | Mitigated by design | `AgentRunner` seam keeps plan/memory/registry invocation-agnostic |
| R7 | Custom-agent workers can't see MCP tools in headless `-p` mode (CLI limitation, confirmed) | Open — root cause known | Not fixable by config (injected & persistent both fail for custom agents, AS-022). Mitigation: orchestrator-as-memory-broker (inject memory into prompts, persist worker-declared notes) — AS-003-aligned |
| R8 | **Outcome quality holds at days / large-DAG scale** (all proof is 42-min / 4-node; error compounds super-linearly) | **Open (AS-029)** | Phase 6.5 instrumented probe on a larger externally-verifiable task; outcome-quality eval as the gating metric |
| R9 | **Self-graded verification** — today's "verify" = tests the agent wrote itself (internal consistency, not external correctness) | **Mitigating (AS-029)** | Verifiable beachhead: external ground truth (tests not authored by the agent, real deploy/run, benchmark, checkable fact) |
| R10 | **Phases 7–8 reinvent a durable agent runtime** that LangGraph/Temporal already provide — contradicts AS-009 (adopt LangGraph as Backend C) | **Open — one-way door (AS-029)** | Resolve bespoke-vs-adopt *before* building Phase 7–8; steelman for bespoke = transparent event log as an earned-autonomy safety asset |
| R11 | **Transfer trap (R-F)** — a check-in/autonomy model built on external verifiability won't transfer to judgment-quality tasks | **Open — design now (AS-029)** | Verifiability-agnostic uncertainty signals (agent confidence, plan ambiguity, irreversibility, novelty-vs-memory); external checks = beachhead calibration only |
| R12 | **Silent under-asking** — the precision-over-recall ping rule, taken literally, → confidently-wrong deliverables on long tasks | **Open (AS-029)** | Phase 9 reframed to *calibrated* checkpointing (not ping-minimization); budget is a constraint on top of calibration |

## Definition of Done (per task, coderAS bar)
Code runs · tests pass · result measured & logged (event log) · `architecture.md` + `handoff.md`
updated · provenance recorded · kgraph map updated.
