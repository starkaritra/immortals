# Immortals — Handoff

> Current state + next actions for the Immortals orchestration project. Rationale lives in
> the decision log below; `architecture.md` is the normative target spec; `plan.md` is the
> phased build order.

## 1. What this is
A manager-orchestrated multi-agent system over the user's existing `AS` agent suite
(coderAS, experimentAS, teachAS, prepAS, researchAS, paperAS, patentAS, presentAS, discussAS).
**managerAS** is the only user-facing agent: it turns a task (structured or vague) into a
typed, validated **plan (DAG)**; a **deterministic Python orchestrator** executes that plan by
invoking worker agents as **headless `copilot` processes** and routing typed **artifacts**
between them through a **local SQLite + MCP** memory substrate.

> **North star (AS-029):** Immortals is **an enterprise-grade expert team you delegate to — a
> "personal JARVIS."** Hand it a task; a **long-running** agent (minutes→days, durable) drives it
> to a **tangible finished outcome**, reaching out **only** when it truly needs you (clarify /
> decide / deliver) — silence is the default, never a notification firehose — and **earns
> autonomy** as it learns you. JARVIS-first, framework-capable. The Phase 0–6 engine is the
> substrate; Phases 6.5–10 (`plan.md`) build the vision on top.

> **End-user product (forward-looking):** the user-facing face of this engine is planned as
> **Immortals Console** — an agent-centric app (agent sidebar + skill library) that consumes this
> core (registry, skills MCP, orchestrator, memory, the `dashboard/` FastAPI base) rather than
> reimplementing it. Greenfield vision/handoff/decisions live in the sister folder
> `../immortals-console/` (separate git lifecycle; not tracked in this repo).

## 2. Current state
- **Phase:** **2 DONE** (memory substrate incl. MCP server) + **Phases 3, 4, 5, 6 DONE**. Phases 0–1
  complete. Forward scope is the **vision roadmap (Phases 6.5–10, AS-029)**: outcome-quality eval →
  durable task lifecycle →
  manager-as-a-service daemon → proactive check-in policy → conversational surface + earned autonomy.
- **Built:** `immortals/` — `contracts/` (4 schemas + validator + models), `registry/` (loader
  with `route()`/`describe()`) + 9 worker manifests, `runners/` (`AgentRunner`, `MockRunner`,
  `CopilotRunner` Backend A — `--output-format json` usage, `mcp_config` + `env_extra` injection),
  `orchestrator/` (deterministic DAG executor: validation, topo-order, seam validation, event
  trail with `run_id`, storage-agnostic sinks, guardrails + approval gate + registry approval
  floor, resume, bounded-parallel scheduler, partial re-runs), `runners/providers/` (**AS-030** —
  normalized `ModelProvider` seam + Anthropic/OpenAI/Gemini/Ollama adapters + `FakeProvider`) and
  `runners/api_backend.py` + `runners/tools.py` (**`ApiRunner` Backend B** — the standalone,
  Copilot-independent backend: persona→system prompt, direct provider calls, self-driven tool loop
  over a workspace-confined approval-gated harness), `memory/` (`MemoryStore` — append-
  only `event/v1` log + `(task_id,id)` artifacts + `notes` KV + agent-namespaced `facts`, schema v3
  w/ migration, append-only triggers, `reconstruct`; **`derived.py`** — `DerivedMemory` projects a
  knowledge graph + a semantic vector index; **`embedding.py`** — pluggable `Embedder` seam + zero-dep
  `HashingEmbedder`; **  `mcp_server.py`** zero-dep stdio JSON-RPC), `cli.py`
  (`run [...] [--share-memory]` · `replay` · `agents [install]` · `route` · `recall` · `memory` ·
  `dashboard` — AS-013..024), and **`dashboard/`** (read-only web inspector — prototype frontend; a
  FastAPI app + single static page with 4 views over a run store; FastAPI/uvicorn behind the optional
  `[dashboard]` extra; the read-half seed of the Phase-8 API — see `design/prototype-frontend-handoff.md`).
  Tests: **247 passing** (240 + 7 for AS-035 settings/provider store).
- **Ship-ready (AS-024):** all paths resolve through `immortals/config.py` (env-overridable, no
  machine-specific hard-coding); the AS personas ship in repo `agents/` (source of truth) and
  `immortals agents install` syncs them into the copilot agents dir. `<name>AS.md` is the locked
  naming convention for all future (incl. auto-inducted) agents.
- **Phase 6 (DONE):** derived memory (AS-023). Agent-namespaced `facts` (with `source` provenance +
  `supersedes`); `DerivedMemory.reindex/search/graph/neighbors` projects events+artifacts+facts into a
  rebuildable knowledge graph (`produced_by`/`contains`/`depends_on`/`supersedes`) and a vector index
  over artifacts+facts; pluggable `Embedder` seam (zero-dep unsigned hashed-BoW default, `sqlite-vec`/
  model is the named future backend). MCP: `memory_search`/`memory_graph`/`memory_add_fact`/
  `memory_list_facts`. CLI: `immortals recall --db --query|--graph [--task-id] [--agent]`. Verified
  live (recall search + graph over a real run).
- **Phase 2 (DONE):** event-sourced store + reconstruction (AS-014); memory MCP server exposing
  artifact/event reads + a shared `notes` KV, injected via `--share-memory` (AS-021); `immortals
  memory register/unregister/status` to manage persistent registration (AS-022). Server verified
  live (default agent wrote a note). **R7 finding (AS-022):** custom `--agent` workers get **no**
  MCP tools in headless `-p` mode (injected *or* persistent — both connect but tools aren't exposed);
  worker-shared memory will come via the orchestrator memory-broker, not worker-side MCP.
- **Phase 3 (DONE):** `Registry.route()` + `agents`/`route` CLI; opt-in `--enforce-approvals` floor (AS-020).
- **Phase 4 (done):** opt-in caps + approval gate, `escalation{reason}`, `blocked` status (AS-015).
- **Phase 5 (DONE):** `--resume` (AS-016), `--max-workers` no-lock scheduler (AS-017), `--from`/`--to`
  partial re-runs (AS-019); live multi-agent run verified.
- **De-risked:** R1/R3/R4 retired; **R2 mitigating** (`cost.total_tokens`, AS-018); **R7 open**
  (custom-agent MCP-tool exposure, AS-021).
- **managerAS authored & wired:** `~/.copilot/agents/managerAS.md` (routes via `agents`/`route` CLI;
  "managerAS in the loop"; invokes the CLI seam).
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

### [AS-035] Model-provider settings — configurable keys/endpoints + OpenAI-compatible custom providers
- Date: 2026-07-09
- Status: accepted (implemented)
- Context: Users need to configure API keys per provider and add local/OSS models (Qwen, GLM,
  DeepSeek, Llama via Ollama/LM Studio/vLLM) and aggregators (Groq, OpenRouter, Together) from the
  UI — not only via env vars.
- Decision: `dashboard/settings.py` — a server-side `SettingsStore` (JSON at `config.settings_file()`
  under the user's home, perms-restricted) holding provider configs `{id,label,adapter,base_url,
  api_key,model,enabled}`; a **suggested catalogue** (Anthropic/OpenAI/Gemini/Groq/OpenRouter/
  Together/DeepSeek/Ollama/LM Studio/vLLM); and `build_provider(store, id)` resolving a config to a
  live provider + model. **Key insight:** every OSS/local host is OpenAI-compatible, so the `openai`
  adapter + a custom `base_url` covers "add your own". Endpoints: `GET /api/settings/catalog`,
  `GET/PUT/DELETE /api/settings/providers`. `RunManager` resolves the run's provider from the store
  (falling back to a bare adapter name + env keys).
- Rationale: one adapter (openai+base_url) unlocks the whole OSS/local ecosystem; keys stay
  server-side and are **masked** on read (browser never re-receives a full key); nothing logs keys.
- Consequences: unblocks the Console settings page + a dynamic provider dropdown. Follow-ups: a
  connectivity "test" button, per-agent default provider. Tests: `test_settings.py` (masking,
  keep-key-on-edit, delete, custom base_url resolution).

### [AS-034] Authoring API — create agents & skills from the Console
- Date: 2026-07-09
- Status: accepted (implemented)
- Context: The Console's "+ Add agent" / "+ Add skill" flows need the engine to scaffold a new agent
  (persona + capability manifest) or skill (SKILL.md + index) as first-class suite assets.
- Decision: `dashboard/authoring.py` — `POST /api/agents` writes a `registry/<name>.json`
  (validated against `registry/v1`) + `agents/<name>.md` persona (frontmatter + body); `POST
  /api/skills` writes `skills/<name>/SKILL.md` (frontmatter template) then regenerates
  `skills/INDEX.json` via `scripts/gen_skill_index.py`. Writes target the engine's asset dirs
  (env-overridable via `config`), the source of truth `agents install` syncs from.
- Rationale: reuses the existing registry/v1 contract + skill-index generator; validates before
  writing; names are slug-guarded and never overwrite (409) — safe mutation.
- Consequences: unblocks the Console authoring modals. Follow-ups: edit/delete, prompt-lint gate on
  create, and richer persona templates. Tests: `test_authoring.py` (agent + skill create, bad
  input, no-overwrite) with asset dirs redirected to a temp home.

### [AS-033] Goal→plan orchestration endpoint (managerAS + a deterministic route planner)
- Date: 2026-07-09
- Status: accepted (implemented)
- Context: The Console needs the full "manager orchestrates a team" flow from the UI: a plain-English
  goal → a real multi-node `plan/v1` → a live DAG run. Two needs: a planner that works **without a
  key** (so the DAG can be demoed/tested), and the real managerAS LLM planner.
- Decision: `dashboard/planner.py` with two planners returning a validated `Plan` — `plan_via_route`
  (deterministic: `registry.route(goal)` picks the top agents and chains them into a small pipeline;
  no LLM) and `plan_via_manager` (prompts the managerAS persona via a provider to emit plan/v1 JSON,
  then extracts + validates it). `POST /api/orchestrate` {goal, planner=route|llm, backend, provider,
  model} builds the plan and runs it through the existing `RunManager` (background + WS streaming),
  returning `{task_id, plan}`.
- Rationale: `planner=route` + `backend=mock` gives a fully key-free, deterministic multi-node run
  (demo + tests); `planner=llm` is the real manager. Reuses the write API/broker/WS unchanged.
- Consequences: unblocks the Console's managerAS orchestration mode + live DAG. Follow-ups: plan
  editing/approval before run; managerAS re-planning on node failure. Tests: `test_orchestrate.py`
  (route planner, LLM planner via FakeProvider, end-to-end mock run).

### [AS-032] Projects API (kgraph-backed) + live tool/terminal streaming from ApiRunner
- Date: 2026-07-09
- Status: accepted (implemented)
- Context: The Console needs project-scoped work (a project = a local folder the agents operate in),
  a file-tree view, and Codex-style live streaming of the agent's tool calls / terminal output into
  the chat. Two engine gaps: no project concept exposed, and `ApiRunner` ran its tool loop silently
  (only the final artifact surfaced).
- Decision:
  - **kgraph is the project context store** (owner's choice): projects come from the per-user kgraph
    knowledge map (`config.projects_source()`, env `IMMORTALS_KGRAPH`), not a new JSON store. New
    `dashboard/projects.py`: `GET /api/projects` (list), `/tree` (pruned, confined file tree),
    `/file` (confined read), `/context` (kgraph recall for the project), `POST /api/projects`
    (register/refresh a project's kgraph map). Browsing is restricted to registered project roots +
    a path-traversal guard.
  - **`ApiRunner` gains an `on_event` hook** emitting `agent_message` / `tool_call` / `tool_result`
    during the loop. The write API's `RunManager` wires it to the `RunBroker`, so tool/terminal
    activity streams over the same `WS /ws/tasks/{id}`. `POST /api/tasks` accepts `project` (→ the
    agent's workspace = tool-harness root).
- Rationale: reuses kgraph (no duplicate project store); streaming reuses the existing broker/WS with
  zero orchestrator change; file access is least-privilege (registered roots only).
- Consequences: unblocks the Console's project selector + file tree + tool-in-chat. Follow-ups:
  project file *watch*/refresh, and persisting tool events to the log (currently live-only). Tests:
  `test_projects_api.py` (kgraph stubbed via env) + ApiRunner `on_event` test.

### [AS-031] Phase-8 write API — manager-as-a-service (POST /api/tasks + live WebSocket)
- Date: 2026-07-09
- Status: accepted (implemented)
- Context: The read-only `dashboard/` was designed as the *read half* of the Phase-8
  manager-as-a-service API; with Immortals Console now committed (Split architecture, its CON-004),
  the write half is in scope: submit a task and watch it run, over HTTP. Runs are long-lived, so a
  request must not block on a whole DAG.
- Options considered:
  - **Background thread + thread→async broker for a WebSocket** — pros: non-blocking submit; live
    events reuse the orchestrator's existing `event_sink`; persists to the same store the read API
    serves; no new heavy dep. cons: we own a small thread/loop bridge.
  - **Synchronous POST that blocks until done** — simple, but useless for minutes-long runs.
  - **A separate task queue (Celery/RQ) / process** — robust at scale, but heavyweight for a
    local-first single-user app now (defer).
- Decision: add `immortals/dashboard/runs_api.py` (separate module so the read surface stays
  isolated): `POST /api/tasks` starts an orchestrator run in a background thread and returns the
  task id immediately; `WS /ws/tasks/{task_id}` streams `event/v1` records via a `RunBroker`
  (`loop.call_soon_threadsafe`), replaying the persisted backlog on connect then streaming live
  (de-duped by `event_id`) so connect-timing never loses events; `GET /api/tasks/{id}/status` is a
  thin status probe. Default backend `mock` (deterministic, no external calls); the frontend passes
  `backend="api"`. Wired via `attach_write_api(app, db_path)` from `create_app`.
- Rationale: smallest non-blocking design that reuses the orchestrator + event store unchanged;
  read endpoints untouched; testable now with FastAPI `TestClient` (incl. websockets) and the mock
  backend — no keys/network.
- Consequences: this is the API the Console frontend consumes (its Track 3). Follow-ups: auth,
  cancellation, and multi-run scale-out (task queue) are deferred; a run-store-per-task vs shared
  store policy can evolve. Tests: `test_write_api.py` (+6) and an ApiRunner-through-Orchestrator
  integration test (+1).

### [AS-030] Backend B — standalone direct-API AgentRunner + provider-adapter layer
- Date: 2026-07-09
- Status: accepted (implemented)
- Context: The only real worker backend was `CopilotRunner`, which shells out to the `copilot` CLI —
  coupling the whole suite to Copilot. The end-user product (Immortals Console) must be a
  **standalone**, Copilot-independent app (bring-your-own API key or a local Ollama). Per the
  Console's CON-004 (Split) + CON-007, this Copilot-independence is an **engine** concern: a new
  runner, not a UI feature.
- Options considered:
  - **New `AgentRunner` implementing direct provider calls** — pros: reuses the AS-009 swappable
    seam; orchestrator/contracts/memory/guardrails unchanged; testable with a fake provider. cons:
    the engine now owns a tool-call loop + a tool harness.
  - **Embed an OSS agent host / LangGraph** — pros: inherit a tool ecosystem. cons: heavier dep,
    UX/semantics shaped by their model, integration friction; the AS-009 note already earmarked this
    as a *later* option, not the standalone MVP.
- Decision: add **`ApiRunner`** (`immortals/runners/api_backend.py`, `name="api"`) plus a
  provider-adapter layer (`immortals/runners/providers/`) with **all four wrappers** — Anthropic,
  OpenAI, Gemini, Ollama — behind one normalized `ModelProvider` interface, and a deterministic
  `FakeProvider` for tests. The runner loads the persona from `agents/<name>.md` (frontmatter
  stripped) as the system prompt, composes the user turn with upstream artifacts fenced as **data**
  (AS-003 injection containment), and drives the tool-call loop itself via a workspace-confined,
  approval-gated `ToolHarness` (`immortals/runners/tools.py`). Wired into the CLI as
  `run --backend api [--provider {anthropic,openai,gemini,ollama}] [--model …]`.
- Rationale: satisfies the standalone requirement at the correct layer with zero change to the
  orchestrator/contracts; provider SDKs are **optional extras** (`pip install "immortals[anthropic]"`
  etc.), keeping the lean core (jsonschema-only) intact; keys are read from env, never logged.
- Consequences: unblocks Immortals Console's whole build (its Track 1). Follow-ups: streaming is
  best-effort per adapter (WebSocket streaming is the Console's Phase-8 API concern); live
  provider round-trips are gated behind env keys (skipped in CI). Tests: `test_providers.py` (pure
  translation, no network) + `test_api_backend.py` (loop/harness via FakeProvider) — +22 tests.

### [AS-028] Rebrand to "Immortals" — product/package rename (Tiers 1+2), AS personas retained
- **Date:** 2026-06-27
- **Status:** accepted.
- **Context:** the system is renamed from **AgentSuite** to **Immortals**. The "AS" suffix
  (Agent Suite) is woven through three tiers with very different blast radii: (1) brand strings,
  (2) the Python package / CLI module / `AGENTSUITE_*` env vars, (3) the 10 `<name>AS.md` personas
  and the immutable `AS-NNN` decision anchors. A blanket rename of (3) is high-risk and largely
  semantic.
- **Options considered:**
  - Brand only (Tier 1) — cheap, but leaves `python -m agentsuite` / `AGENTSUITE_*` mismatched
    with the brand; confusing once published (AS-025). Pro: zero code risk. Con: half-rebrand.
  - Brand + package (Tiers 1+2) — rename `agentsuite/`→`immortals/`, `AGENTSUITE_*`→`IMMORTALS_*`,
    `python -m agentsuite`→`python -m immortals`; keep personas + anchors. Pro: clean public
    identity before the unpublished v0.0.1 ships (cheap now, a one-way door after PyPI). Con:
    ~340 mechanical edits across 47 files.
  - Full sweep (Tiers 1+2+3) — also rename 10 installed personas to `*IM` and re-anchor decisions.
    Pro: total consistency. Con: violates the immutable-anchor ADR rule; rewrites user-facing
    personas referenced everywhere; high risk, low value.
- **Decision:** **Brand + package (Tiers 1+2).** Conceptual split: **Immortals = the orchestration
  system; the AS agents are "the immortals" it commands.** Personas keep the `<name>AS.md`
  convention; `AS-NNN` anchors stay immutable; `patrecAS/` keeps its name.
- **Rationale:** v0.0.1 is unpublished and has **no git remote**, so the package rename is a cheap
  reversible edit *now* and an expensive one-way door *after* the AS-025 publish — do it first.
  Keeping personas/anchors respects the immutable-anchor rule and avoids a risky, low-value rewrite.
- **Consequences:** managerAS's persona updated its `python -m agentsuite …` command strings to
  `python -m immortals …`; `pyproject` name/packages/package-data updated; kgraph project renamed.
  **Local repo folder rename** `C:\Code\AgentSuite`→`C:\Code\Immortals` is deferred (would orphan
  the path-keyed
  kgraph memory + this session cwd) — a deliberate manual follow-up. A console-script entry point
  (`immortals`) is folded into the packaging-polish workstream.
- **Links:** AS-024 (config seam carrying the env vars), AS-025 (publish — why now beats later).

### [AS-029] North-star vision — Immortals as a delegated, long-running expert team ("personal JARVIS")
- **Date:** 2026-06-27
- **Status:** accepted (vision; supersedes nothing — it *frames* AS-025/026/027 under one north star).
- **Context:** the engine (Phases 0–6) is mature but its forward scope was three deferred-but-locked
  bets (AS-025 publish + conversational surface, AS-026 desktop bubble, AS-027 patrecAS adaptive
  learning) with no single north star tying them together. Vision scoping session (2026-06-27)
  established that.
- **North star:** **Immortals is an enterprise-grade expert team you delegate to — a "personal
  JARVIS."** You hand it a task in plain English; it runs as a **long-running agent** (minutes to
  days, durably, surviving reboots) that works autonomously toward a **tangible finished outcome**,
  and reaches out **only** when it genuinely needs you (a clarification, a real decision fork, or to
  deliver) — never a notification firehose. As it learns what you accept/dismiss, it **earns more
  autonomy.** The owner is the primary user; the engine stays general enough for others to repurpose
  (**JARVIS-first, framework-capable**).
- **Scope corrections locked (what it is NOT):**
  - **Task-scoped, not life-watching.** "Proactive/ambient" means it drives *the task it was handed*
    and surfaces task-relevant moments — it does **not** surveil the owner's whole context/screen/life.
  - **Tangible outcomes, not chat.** The unit of delivery is a finished deliverable, not a reply.
  - **Silence is the default.** A push notification must *earn* its interruption: high-precision,
    low-volume, rate-limited, quiet-hours — explicitly **not** Swiggy/Zomato-style incessant pings.
    The false-positive (annoying ping) cost ≫ the false-negative (missed suggestion) cost.
  - **Earned autonomy.** Starts suggest-only; graduates to acting on low-risk items as it learns the
    owner (patrecAS/learnAS-gated, AS-027) — propose-not-apply remains the safety floor.
- **Lifecycle decision:** design for the **hardest case (days)**; minutes is the trivial case.
  Tasks become **first-class durable entities** (lifecycle states) layered on the existing
  event-sourced store; a **daemon/manager-as-a-service** (AS-025) loads in-flight tasks on startup
  and resumes them (the `--resume`/event-log spine already exists, AS-016); the synchronous approval
  gate generalizes to an **async park/resume** (`waiting_on_human`) so a task can wait hours/days
  for the owner without holding a process.
- **Architecture delta (what's new vs Phases 0–6):** ① durable task lifecycle, ② manager-as-a-service
  daemon + streaming API, ③ the **proactive check-in policy** (the WHEN-to-interrupt engine — the
  genuinely novel, patent-worthy core; precision over recall), ④ conversational surface + earned
  autonomy. The plan→execute→artifact engine, event-log durability, resume, guardrails, approval
  gate, and derived memory are the **substrate** these layer onto — not a rewrite.
- **Consequences:** Phase 7 is re-scoped from a generic "inventive" grab-bag into a concrete vision
  roadmap (Phases 6.5–10, see `plan.md`); AS-025/026/027 become the named sub-bets of this north star;
  the check-in policy (Phase 9) is the priority research/IP artifact. The existing generic Phase-7
  items (Backend C, self-experimentation, contract-typed routing, reflection/critic) fold in as
  supporting work, not the headline.
- **Open (deferred to the build):** the precision/relevance threshold + notification budget design;
  manager driver shape (shell `managerAS -p` per turn vs a thin Python manager — AS-025 open Q);
  voice now vs text-first; the MVP cut (smallest slice of Phases 7–9 that delivers "delegate → walk
  away → tangible result with earned-trust check-ins").
- **Stress-test refinements (discussAS red-team, 2026-06-27):** the vision held up; the
  `innovation-digest` run (§`design/evidence/…`, n=1, 8/8 + 78/78) is real proof of the mechanism at
  **minutes-scale**. The red-team sharpened five things, now binding on the roadmap:
  1. **Eval-first (keystone moved earlier).** The true keystone is an **outcome-quality eval
     harness**, which sits **before Phase 7** — *not* in "supporting/parallel." You cannot tune the
     Phase-9 check-in threshold, bound Phase-10 autonomy safely, or *detect* days-scale drift without
     a ground-truth quality signal. → new **Phase 6.5** in `plan.md`.
  2. **Verifiable beachhead → expand (owner's call).** Start with a **small set of externally-
     verifiable, code-shaped tasks** (the proven domain), where the eval reduces to "did the external
     check pass?"; scale to judgment-quality tasks later. This retires the *self-graded-homework*
     risk (today's "verify" = tests the agent wrote itself) and makes silent drift detectable.
  3. **R-F, the transfer trap (design against it NOW).** Do **not** build the check-in / earned-
     autonomy model *on top of* external verifiability, or it won't transfer to judgment-quality
     tasks that have no external check. **Design principle:** uncertainty signals must be
     **verifiability-agnostic** (agent confidence, plan ambiguity, decision irreversibility,
     novelty-vs-memory); external checks are *beachhead calibration ground-truth only* — the crutch
     must not become a load-bearing wall.
  4. **Phase 9 reframed.** From *"minimize pings"* to **"calibrated uncertainty checkpointing under a
     notification budget."** The objective is calibration; anti-spam is a *constraint on top* — not
     the goal. (The run's own after-action review supports this: the one real pain was a comms gap,
     fixed by *more* narration.) The precision-over-recall ping rule, taken literally, pushes toward
     dangerous **under-asking** → silent-wrong deliverables; calibration is the corrective.
  5. **Backend-C gate (one-way door).** Phases 7–8 hand-build a durable task lifecycle + daemon that
     LangGraph/Temporal already provide — and AS-009 *plans to adopt* LangGraph as Backend C. Resolve
     **bespoke-vs-adopt before building Phase 7–8** (legit steelman for bespoke: the transparent event
     log is a real safety asset for earned autonomy that a framework won't replicate). See new R10.
- **Links:** AS-025 (manager-as-a-service + conversational surface — the spine), AS-026 (bubble
  client), AS-027 (patrecAS earned autonomy), AS-016 (resume spine), AS-006/014/023 (memory
  substrate), AS-008/009 (eval_platform reuse + Backend C — the R10 gate).

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

### [AS-025] Publish + manager-as-agent + conversational surface (proposed, scope)
- **Status:** proposed (direction locked; build deferred).
- **Context:** ship Immortals publicly and give it a natural always-available voice/chat surface.
- **Decisions locked with owner:** publish to **PyPI + public GitHub**; **the manager is itself an
  agent** (not bespoke glue); the front surface is a **Gemini/Alexa-style conversational assistant**
  the user converses with.
- **Suggested approach (the seam):** introduce a **manager-as-a-service** layer — a small local
  service (FastAPI, bound to `127.0.0.1` + token) exposing a versioned, streaming API
  (**WebSocket**, so clarifying questions + approval gates render interactively). The manager loop
  behind it either (i) shells out to `copilot --agent managerAS -p` per turn, or (ii) becomes a thin
  Python "manager driver" (LLM-plans → registry routing → orchestrator) — option (ii) is the clean
  long-term seam and aligns with Backend C. For the **Alexa/Gemini conversational feel**: add a
  voice layer over the same API — local **STT** (e.g. `faster-whisper`) + **TTS** (e.g. Piper) +
  wake-word (e.g. openWakeWord), all local-first to preserve the no-third-party-data posture; the
  desktop bubble (AS-026) is its visual client. Packaging: console entry point `immortals`, ship
  `registry/`+`agents/` as wheel data, GitHub Actions (pytest), Apache-2.0, SemVer `v0.1.0`.
- **Open questions:** manager driver (i) vs (ii); voice now vs text-first; cloud vs fully-local STT/TTS.
- **Links:** AS-024 (config seam), AS-026 (frontend), architecture "Backend C".

### [AS-026] Desktop floating-bubble frontend — Tauri (proposed, scope)
- **Status:** proposed (framework locked; build deferred).
- **Context:** a floating, always-on-top "bubble" on Windows/Linux that opens a chat assistant.
- **Decision:** **Tauri** (Rust + system webview) for the shell — tiny footprint, frameless
  always-on-top + system tray, cross-platform, secure. It is a **thin client** to the AS-025
  manager-as-a-service API (WebSocket streaming); all orchestration logic stays server-side so the
  same API also serves a future web app / VS Code extension / voice surface.
- **Consequences:** chat UI as a small web frontend embedded in Tauri; must render streamed
  clarifying-questions + approval-gate prompts; local-only binding + token. Adds a Rust toolchain.
- **Links:** AS-025 (the API it talks to).

### [AS-027] patrecAS/learnAS — adaptive-learning module as a root-level component (proposed, scope)
- **Status:** proposed (structure + research locked; build deferred).
- **Context:** AS-012's planned meta-learning layer becomes a first-class module that learns the
  user's patterns, adapts agent behaviour, and inducts new agents when the roster has a gap.
- **Decisions locked with owner:** surface it as its **own root-level folder** (`patrecAS/`, alias
  learnAS) with its **own `design/` docs maintained separately inside it**; **researchAS runs a deep
  dive** to ground the approach and author those docs.
- **Suggested framing (to be validated by the deep dive):** "RLHF-type" here means **preference-based
  adaptation over the controllable surface (agent prompts, routing, manifests, the roster)** — *not*
  gradient RLHF on the copilot LLM weights (not ownable). Sequence: (A) retrieval-based
  personalization on the Phase-6 memory (facts + vectors) → (E) **new-agent induction** (gap-detect
  from low `route()` scores → generate a `<name>AS.md` persona + `registry/v1` manifest → human
  approve → install via AS-024) → (B) approved, versioned, A/B-evaluated prompt/manifest diffs →
  (C) contextual bandit over routing/templates with a learned reward model → (D) DPO/RLHF only if a
  self-hosted planner is adopted. **Safety rails (non-negotiable):** propose-not-apply, git-versioned
  + human-approved + reversible agent edits, experimentAS A/B before adopting (anti-Goodhart),
  local-first privacy with reset/opt-out.
- **Consequences:** reward signal sourced from the AS-025 UI + the AS-006 event log; the registry's
  "new manifest routable with no code change" design makes induction tractable.
- **Links:** AS-012, AS-006 event log, Phase 6 memory (AS-023), AS-024 (`agents install`), AS-025 UI.

### [AS-024] Path decoupling + persona bundling — ship-ready packaging hygiene
- **Status:** accepted.
- **Context:** prerequisite for publishing (#1) and for the frontend (#2) / learnAS (#3) seams: the
  project must run unchanged on any machine, not just the author's checkout. Hard-coded paths lived
  in `managerAS.md` (`C:\Code\Immortals`, `.venv\Scripts\python.exe`); persona `.md` files lived
  only in the author's `~/.copilot/agents/`.
- **Options considered:**
  - Central config module + env overrides — pros: one place, testable, CI/packaged/dev parity;
    cons: a little indirection.
  - Sprinkle `os.environ.get` at call sites — pros: minimal; cons: scattered, undiscoverable.
- **Decision:** added `immortals/config.py` — every filesystem location resolves through it with an
  env override (`IMMORTALS_HOME`/`_REGISTRY_DIR`/`_AGENTS_DIR`/`_COPILOT_BIN`, `COPILOT_AGENTS_DIR`,
  `IMMORTALS_MCP_CONFIG`), defaulting off the install location. Wired `Registry.load`, `CopilotRunner`,
  and the CLI mcp-config default through it. **The AS personas now ship in the repo** at `agents/`
  (10 files: 9 workers + managerAS), de-hardcoded; `immortals agents install [--dest] [--force]`
  syncs them into the copilot agents dir (idempotent, never clobbers user edits without `--force`).
- **Locked conventions:** (1) **personas ship with the package** (source of truth = repo `agents/`);
  (2) the **`<name>AS.md` naming convention is canonical for all future inducted agents** (incl. any
  learnAS auto-induction). A guard test asserts no `C:\Code`/author-name strings remain in the package.
- **Rationale:** removes one-way-door friction before going public; gives a clean, reusable config
  seam for the frontend service and learnAS; keeps the zero-dep, local-first posture.
- **Consequences:** 15 new tests (159 total). Wheel packaging of the sibling `registry/`+`agents/`
  dirs (so they ship in a built wheel, not just source/editable installs) is deferred to the publish
  ADR (AS-025). No behaviour change for existing source-checkout runs.
- **Links:** `immortals/config.py`, `registry/loader.py`, `runners/copilot_backend.py`, `cli.py`
  (`agents install`), `agents/`, `tests/test_config.py`.

### [AS-023] Phase 6 derived memory — knowledge graph + semantic vector index (pluggable, zero-dep default)
- **Status:** accepted.
- **Context:** Phase 6 — give the manager semantic recall over prior artifacts/facts and a
  navigable knowledge graph. `architecture.md` named `sqlite-vec`, but the memory layer so far is
  zero-dependency, deterministic, local-first, offline (a stated posture + reproducible tests).
  Forcing `sqlite-vec` + a real embedding model now is a one-way door (deps, cost, flaky CI,
  data-egress for API embedders).
- **Options considered:**
  - Pluggable `Embedder` seam + zero-dep deterministic default — pros: works today, offline,
    deterministic tests, upgrade is a drop-in; cons: brute-force cosine, lower recall at scale.
  - `sqlite-vec` + real model now — pros: best recall/ANN at scale; cons: heavy deps, non-deterministic,
    overkill for the current tiny corpus, CI/offline cost.
  - Zero-dep, no seam — pros: simplest; cons: hard-codes the choice (no upgrade path).
- **Decision:** option **A**. An `Embedder` interface (`memory/embedding.py`) with a default
  `HashingEmbedder` (stdlib hashed bag-of-words, L2-normalized) + brute-force cosine. A
  `DerivedMemory` (`memory/derived.py`) projects the event log + artifacts + a new agent-namespaced
  `facts` table into two rebuildable read-models: a **knowledge graph** (nodes task/agent/artifact/fact;
  edges `produced_by`/`contains`/`depends_on`/`supersedes`) and a **vector index** over artifacts + facts.
  Exposed via MCP (`memory_search`/`memory_graph`/`memory_add_fact`/`memory_list_facts`) and a new
  `immortals recall` CLI. `sqlite-vec` + a real model is reframed as the *named future backend behind
  the seam*, not the MVP — reconciling the architecture doc.
- **Rationale:** right for both MVP and production (the seam makes the upgrade a drop-in, no call-site
  churn), keeps the zero-dep/offline/reproducible posture and deterministic tests, and gives genuinely
  useful recall over the small current corpus. Derived models are *strictly a function of source data*
  (`reindex` wipes+rebuilds), so they can't drift ahead of the log (R5 guard); the `facts.supersedes`
  pointer retires stale facts rather than mutating them (also R5).
- **Sub-finding (embedder weighting):** signed feature-hashing (unbiased inner products, good for ML)
  silently zeroed a genuine single-token match on longer docs when a query's opposite-signed tokens
  collided onto same-sign buckets. Switched the default to **unsigned** hashed bag-of-words so a shared
  token always *increases* similarity — the correct choice for short-text retrieval ranking. Locked by
  a regression test.
- **Consequences:** 22 new tests (144 total). Next: have the orchestrator/manager pull `recall` context
  automatically (broker, AS-022) and, when scale warrants, drop in a `sqlite-vec`/model backend behind
  the `Embedder` seam. Schema migrated v2 → v3 (adds `facts`; derived tables created on demand).
- **Links:** `immortals/memory/{embedding,derived,store}.py`, `mcp_server.py`, `cli.py` (`recall`),
  `tests/test_derived.py`; architecture §"Memory architecture"/"Storage & access"; plan Phase 6.

### [AS-022] Memory registration command + R7 root cause — broker over MCP for workers
- **Status:** accepted.
- **Context:** finish R7 — let custom-agent workers share memory. Hypothesis: a *persistent* MCP
  registration (the channel kgraph uses) would expose the memory tools to custom `--agent` workers
  where `--additional-mcp-config` did not.
- **What was built:** `immortals memory register|unregister|status` — adds/removes the env-resolved
  memory server in `~/.copilot/mcp-config.json` (reversible, preserves other servers; `--config-path`
  override for tests). The server now falls back to a default store (`~/.copilot/immortals/memory.db`)
  when neither `--db` nor `$IMMORTALS_MEMORY_DB` is set, so a global registration stays healthy in
  ordinary sessions.
- **Experiment (decisive):** registered the server persistently, then ran a custom `--agent teachAS`
  worker headless (`-p`) with `IMMORTALS_MEMORY_DB` set. The server **connected**, but the agent
  reported the tools were **not in its function list** and no note was written. Combined with the
  prior runs this establishes: **in headless `-p` mode the copilot CLI exposes MCP tools to the
  default agent but not to custom `--agent` workers — whether injected or persistently registered.**
  Both connect; the tools are simply absent from a custom agent's toolset.
- **Decision:** R7 cannot be retired by registration — it's a CLI limitation, not a config gap. The
  `memory register` command and `--share-memory` injection remain useful for the default agent /
  interactive sessions / a future CLI that lifts the limitation, but **worker-shared memory will be
  delivered by the orchestrator acting as the memory broker** (consistent with AS-003: the
  orchestrator already mediates all agent I/O). Sketch: the orchestrator injects relevant prior
  notes/artifacts into a worker's prompt (read) and persists the worker's output plus any
  structured notes it declares (write) — no worker-side MCP call required.
- **Consequences:** R7 reclassified (root cause known; mitigation = broker). README corrected. The
  broker is the recommended next slice; it defines a small worker-output notes convention (a design
  choice worth confirming before building). The environment was left as found (server unregistered).

### [AS-021] Memory MCP server — shared worker memory over stdio (Phase 2 remainder)
- **Status:** accepted (with a documented CLI constraint).
- **Context:** AS-006/007 call for workers to read/write shared memory over MCP. Finish Phase 2 by
  exposing the SQLite store as an MCP server injected into workers.
- **Options considered:**
  - Official `mcp` Python SDK / FastMCP — pro: standard; con: adds a dependency, diverges from the
    user's existing zero-dep kgraph MCP server.
  - **Hand-rolled stdio JSON-RPC 2.0 server (zero deps)** — mirrors `kgraph_mcp.py`, matches
    Immortals's lean-deps ethos (only `jsonschema`). Chosen.
- **Decision:** `immortals/memory/mcp_server.py` — newline-delimited JSON-RPC 2.0 over stdin/stdout,
  exposing `memory_{get_artifact,list_artifacts,put_note,get_note,list_notes,recent_events}`. The
  store gains a `notes` KV scratchpad (schema **v2**, with a v1→v2 migration) plus `busy_timeout`
  for concurrent orchestrator+worker access. The server resolves its DB from `--db` or
  `$IMMORTALS_MEMORY_DB`. Delivery seams: `run --share-memory` injects the server via
  `--additional-mcp-config` (bound to `--db`) **and** sets `IMMORTALS_MEMORY_DB` on the worker so a
  persistently-registered server resolves the same store. `dispatch`/`call_tool` are split out for
  unit-testing without I/O.
- **Verification:** the server is correct end-to-end — unit + a live subprocess stdio test, and a
  **live worker (default agent) called `memory_put_note` and the note persisted** to the shared store.
- **CLI constraint (verified, documented):** copilot **custom `--agent` workers do not receive
  `--additional-mcp-config` tools** in this CLI version (the server connects and serves `tools/list`,
  but its tools aren't placed in a custom agent's function list — only the default agent's). A
  workspace `.mcp.json` is **not loaded** in `-p` non-interactive mode. The proven channel to custom
  agents is the **user persistent config** (`~/.copilot/mcp-config.json`, as kgraph demonstrates).
- **Consequences:** for custom-agent workers, register the env-resolved server **once** (opt-in, not
  done automatically — a global-config change):
  `copilot mcp add immortals-memory -- <venv-python> -m immortals.memory.mcp_server`
  The orchestrator already injects `IMMORTALS_MEMORY_DB` per run, so the registered server binds to
  the active store. Until then, the orchestrator remains the single writer of artifacts/events to the
  shared store (workers' returned artifacts are persisted centrally), so cross-run memory and audit
  are intact; only *worker-initiated* shared reads/writes await the registration. Risk **R7** added.

### [AS-020] Phase 3 routing — registry-driven agent selection + approval floor
- **Status:** accepted.
- **Context:** Phase 3's goal is "adding an agent = adding a manifest; the manager picks it with no
  orchestrator change." Two needs: (1) a way for managerAS to discover/route to agents from the
  registry; (2) registry-driven policy. Static artifact-*type* checking of the DAG was considered
  but is **not groundable yet** — plans carry artifact *ids*, not types, and real runners emit a
  generic `agent_response` type, so a strict produces/consumes type check would reject every live
  run. Deferred until plans carry types or runners emit semantic types.
- **Decision:**
  - **Routing API + CLI.** `Registry.route(need, top=…)` ranks manifests deterministically (no LLM):
    normalised capability-phrase hits (heavy), capability-token overlap (medium), and
    `when_to_use`/`summary` overlap (light), returning `{agent, score, reasons, …}` sorted by score
    then name. `Registry.describe()` returns the full catalogue. CLI: `immortals agents` (list) and
    `immortals route --need "<text>" [--top N]` — the tools managerAS calls to route, so a new
    agent is reachable the moment its manifest exists.
  - **Approval floor (opt-in).** `Orchestrator(enforce_registry_approval=True)` makes a manifest's
    `approval_default: required` a sign-off *floor*: a node may *raise* approval but not lower it.
    Off by default (non-breaking); CLI `run --enforce-approvals`. Registering a high-stakes agent
    (experimentAS/coderAS/patentAS) thus auto-gates its nodes with zero code change.
- **Rationale:** delivers the Phase 3 exit (manifest-driven routing + policy, no orchestrator
  change) with fully groundable mechanisms; keeps routing deterministic/auditable and the approval
  floor configurable (no hard-coded policy).
- **Consequences:** managerAS persona updated to route via `agents`/`route` rather than a hardcoded
  list. Static DAG type-checking remains a future item (needs typed plan nodes or semantic runner
  output). Phase 3 complete.

### [AS-019] Partial re-runs — execute a selected sub-graph (`--from` / `--to`)
- **Status:** accepted.
- **Context:** Phase 5's last item: re-run only part of a DAG (e.g. after editing one node's
  prompt) without recomputing the whole plan, reusing persisted upstream artifacts.
- **Decision:** `run(plan, from_node=…, to_node=…)` computes a **selection** = descendants-of-`from`
  ∩ ancestors-of-`to` (either bound optional). Selected nodes are **force-run** (never resume-skipped,
  so editing + re-running recomputes them); non-selected nodes are treated as resolved and their
  outputs are sourced from the seeded store. Before executing, every selected node's data inputs are
  validated to be either produced by another selected node or present in the seed — otherwise a
  `PlanError` tells the user to widen the slice or run upstream first. A `decision` event records the
  selection. CLI: `run --from NODE` / `--to NODE`; `--from` requires `--db` (needs upstream
  artifacts); `--to`-only needs no store (all ancestors are in-slice). Re-running overwrites the
  artifact in the store (upsert), so partial re-runs are idempotent and update-in-place.
- **Rationale:** turns the event-sourced store + readiness scheduler into a precise re-execution
  tool; the ancestor/descendant intersection is the standard build-system slice semantics.
- **Consequences:** Phase 5 is complete. Verified: `--to left` runs {root,left}; `--from left` runs
  {left,sink} sourcing `right.art` from the store; re-run overwrites only the selected artifact.

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
- **Decision:** `immortals/orchestrator/guardrails.py` — a frozen `Guardrails(max_total_tokens,
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
- **Decision:** `immortals/memory/store.py` `MemoryStore` over local SQLite — an **append-only
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
  deterministic orchestrator as a tool** (MVP: `shell` → `python -m immortals run --plan-file
  …`; production: the orchestrator MCP server). **Only worker agents run headless**, spawned by
  the orchestrator. managerAS is never the headless one on the normal path.
- **Consequences:** a headless managerAS (no intake, autonomous assumptions) is kept as a
  **future automation mode** for self-experimentation / patrecAS-driven runs, reusing the same
  `python -m immortals run` seam. Build target: a CLI `run` command + managerAS wired to call
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
5. ✅ **Phase 2 MCP slice** — memory MCP server (`immortals/memory/mcp_server.py`) + `notes` KV
   (schema v2); injected via `run --share-memory` + `IMMORTALS_MEMORY_DB`. Verified live (default
   agent). Custom-agent worker exposure needs a one-time persistent `copilot mcp add` (AS-021, R7).
6. ✅ **Real usage/cost** — `CopilotRunner` parses `--output-format json` and reports
   `cost.total_tokens`; the `max_total_tokens` guardrail now bites on real runs (AS-018).
7. ✅ **Phase 5 complete** — partial re-runs (`--from`/`--to`, AS-019) + a verified live 2-agent
   end-to-end run (experimentAS → teachAS).
8. ✅ **Phase 3 complete** — registry-driven routing (`route`/`agents` CLI) + opt-in approval floor
   (`--enforce-approvals`); adding an agent = adding a manifest (AS-020).
9. **Next candidates:** (a) **orchestrator memory-broker** (retires R7 within the CLI limits) —
   inject relevant prior notes/artifacts into worker prompts (read) and persist worker-declared
   notes parsed from output (write); a small worker-output convention worth confirming first;
   (b) **result caching** keyed on the provenance hash (handoff §4) to cut cost on re-runs;
   (c) **Phase 6** — derived memory (graph + vector retrieval); (d) typed-plan artifact checking
   (the deferred half of Phase 3). Refresh the kgraph map alongside.

## 8. Related precedents (reuse, don't reinvent)
- `eval_platform/core/pipeline/runner.py` — composable stage runner (the orchestrator skeleton).
- `eval_platform` versioned JSON contracts + domain-agnostic "ship mechanism, not data" principle.
- `kgraph` — graph memory + MCP server (extend to suite scope for AS-006/AS-007).
- The `AS`-convention agent personas in `~/.copilot/agents/` (the workers).
