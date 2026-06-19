# AgentSuite — Plan

Build order favors a **thin vertical slice that runs end-to-end first**, then deepens each
component. Every phase ends with something runnable and a measured result, not broad stubs.

## Phase 0 — Scaffold & contracts (foundation)
- [x] Decide architecture, invocation backend, storage (see `handoff.md` decision log).
- [x] Verify Backend A feasibility (`copilot --agent X -p … --output-format json`).
- [x] Create the Python package skeleton (`agentsuite/`), `pyproject.toml`, test harness, `.gitignore`.
- [x] Author the JSON Schemas: `plan/v1`, `artifact/v1`, `registry/v1`, `event/v1` + validators + dataclass models.
- [x] Write capability manifests (`registry/<agent>.json`) for the existing AS agents (9 workers).
- **Exit:** ✅ schemas validate sample plans/artifacts; `pytest` green (30 passed).

## Phase 1 — MVP vertical slice (single agent, end-to-end)
- [x] `AgentRunner` interface + **Backend A** implementation (spawn `copilot`, `-s` text → `artifact/v1`). MockRunner for tests.
- [x] Minimal orchestrator: validate plan (schema + registry) → topo-order → invoke via runner → validate seam → aggregate, with event trail.
- [x] **Backend A retired risk R3**: live one-node run (teachAS) succeeded end-to-end via `scripts/smoke_backend_a.py`.
- [x] managerAS persona (planner) authored at `~/.copilot/agents/managerAS.md`; emits `plan/v1`.
- [x] Glue: CLI `python -m agentsuite run --plan-file …` (the orchestrator seam, decision AS-013); managerAS invokes it via shell and synthesizes. `depends_on` made first-class after observing managerAS's natural output.
- **Exit:** ✅ **Phase 1 done.** A live managerAS planning call emitted a valid 2-node `plan/v1`; the CLI executed it in dependency order with a full event trail. Backend A proven on a real worker run.

## Phase 2 — Memory substrate (event log + MCP)
- [x] SQLite schema: `events` (append-only, in-DB triggers) + `artifacts` projection table.
- [x] Event-sourcing writer; orchestrator emits an event per invocation/decision/escalation via
  storage-agnostic `event_sink`/`artifact_sink` (`MemoryStore`, AS-014). `run --db` + `replay` CLI.
- [ ] Local **MCP server** exposing memory read/write; inject into workers via `--additional-mcp-config`.
- [x] Blackboard: artifacts persisted + resolvable by id across nodes/runs.
- **Exit:** ✅ a run is fully reconstructable from the event log (`replay` folds events → status +
  artifacts); ⏭ workers sharing memory via MCP is the remaining slice.

## Phase 3 — Routing & registry
- [ ] Plan validation against the capability registry (type-check `agent`/`inputs`/`produces`).
- [ ] managerAS routes by matching task requirements → agent manifests (no hardcoded routing).
- **Exit:** adding a new agent = adding a manifest; manager can pick it with no orchestrator change.

## Phase 4 — Guardrails & human-in-the-loop
- [x] Budget/token caps, timeouts, max node executions, per-agent invocation cap (loop guard) —
  opt-in `Guardrails` (default unlimited), orchestrator-enforced, structured escalation (AS-015).
- [x] Approval gates (`approval: required`) — orchestrator emits `approval_requested`, consults an
  `approval_handler`, and ends the run `blocked` if unapproved; CLI `--approve` / interactive prompt.
- [x] Escalation path: failure / contract violation / guardrail breach → `node_failed` +
  `escalation{reason}`, returned to the manager (re-plan is manager-side).
- **Exit:** ✅ a capped run halts with the breach reason; an approval-gated node waits for sign-off
  (blocks without it). Note: token cap bites once a runner reports usage (`provenance.cost`).

## Phase 5 — Multi-agent DAG (parallelism, resume)
- [x] Topological readiness scheduler with bounded parallel workers (`--max-workers`); the pool
  runs only `runner.run` while the main thread owns all state — no locks (AS-017).
- [x] `--resume` from the event log (skip completed nodes via the persisted blackboard, AS-016);
  per-run `run_id` keeps `event_id`s unique across re-runs.
- [ ] Partial re-runs (`--from`/`--to` node).
- [ ] End-to-end multi-agent task (e.g. experimentAS designs → coderAS implements → experimentAS analyzes).
- **Exit:** ⏳ parallelism + resume done (independent nodes overlap, verified by a concurrency
  probe; interrupt → resume completes); partial re-runs + a live multi-agent run remain.

## Phase 6 — Derived memory (graph + vector)
- [ ] Project events into the knowledge graph (extend kgraph to suite scope).
- [ ] `sqlite-vec` vector index over artifacts + facts; semantic retrieval for the manager's context.
- [ ] Per-agent namespaced views unifying the existing heterogeneous stores.
- **Exit:** manager retrieves relevant prior artifacts/facts semantically; graph navigable.

## Phase 7 — Future / inventive (scoped, not built)
- [ ] **Backend C** migration (LangGraph/durable or `--acp`) behind the same `AgentRunner`.
- [ ] **Self-experimenting suite**: A/B alternative plans / agent configs, measured via the event log.
- [ ] **Contract-typed routing**: static type-check of plan composition.
- [ ] Reflection/critic loop before artifact acceptance.

## Milestone map
| Milestone | Phases | Demonstrable outcome |
|---|---|---|
| M1 — "It runs" | 0–1 | Manager → orchestrator → one headless worker → answer |
| M2 — "It remembers" | 2–3 | Event-sourced, MCP-shared memory; registry-routed |
| M3 — "It's safe & parallel" | 4–5 | Guardrails, approval gates, resumable multi-agent DAG |
| M4 — "It learns & migrates" | 6–7 | Semantic memory; Backend C path; self-experimentation |

## Risk & assumption register
| # | Risk / assumption | Status | Mitigation |
|---|---|---|---|
| R1 | Backend A can run a named agent headlessly & return parseable output | **Retired** | Verified: `--agent`, `-p`, `--output-format json`, `--no-ask-user`, `--allow-all-tools` |
| R2 | Headless worker latency/cost is acceptable for multi-node DAGs | **Mitigating** | Usage now measured per run (`cost.total_tokens`/durations from `--output-format json`, AS-018); budget caps + parallelism in place; caching next |
| R3 | Nested `copilot` invocation (CLI-in-CLI) behaves cleanly | **Retired** | Live smoke test: `scripts/smoke_backend_a.py` ran teachAS headless end-to-end, valid artifact returned |
| R4 | Manager reliably emits schema-valid plans | **Retired** | Live managerAS planning call emitted a valid 2-node `plan/v1`; `depends_on` made first-class to match its natural output; reject-and-retry still available |
| R5 | Memory-poisoning / stale facts across runs | Open | Provenance on every fact; supersede edges; injection containment |
| R6 | Backend C migration stays cheap | Mitigated by design | `AgentRunner` seam keeps plan/memory/registry invocation-agnostic |

## Definition of Done (per task, coderAS bar)
Code runs · tests pass · result measured & logged (event log) · `architecture.md` + `handoff.md`
updated · provenance recorded · kgraph map updated.
