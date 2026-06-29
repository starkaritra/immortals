# Handoff → coderAS: Prototype frontend (read-only run/memory dashboard)

> **Type:** single-task build brief (not the master state doc — that's `design/handoff.md`).
> **Author:** discussAS · **Date:** 2026-06-27 · **Anchors:** AS-029 (north star), `plan.md`
> Phase 6.5 + Phase 8. **Stress-tested:** yes (the build-vs-defer decision below is the output of a
> discussAS red-team — read §1 so you don't "improve" it back into scope creep).

## 1. Why this exists (context — read before coding)
Immortals is a manager-orchestrated multi-agent system (Phases 0–6 done). The north star (AS-029)
is "a team you delegate to": hand it a task → a long-running agent returns a tangible outcome,
pinging you only when it matters. The full interactive UI (submit a task, answer check-ins) is
**Phase 10** and depends on a daemon/API that **does not exist yet** (Phase 8).

This task is the deliberately-scoped slice we *can* build now without pulling the roadmap forward:
a **localhost, read-only web inspector** over the **existing** `run --db` SQLite store + derived
memory. It earns its keep three ways:
1. **Makes the system tangible** (the owner is motivated by seeing it work).
2. **It's the inspection tool for the Phase-6.5 eval probe** — finding where a run silently drifted
   is far easier here than in `replay --pretty` JSON.
3. **It is the read-half of the Phase-8 manager-as-a-service API** — the GET endpoints survive into
   Phase 8; later you add write endpoints and it *becomes* the real UI. **Nothing is throwaway.**

> ⚠️ **The whole point is that it stays small and on-path.** If you find yourself adding a "submit
> task" button, auth, live-streaming, or a bubble window — **stop**, that's Phase 8/10, out of scope
> (§5). Surface it as a follow-up instead of building it.

## 2. Mandate
Build `immortals dashboard --db <path> [--port N]`: a local FastAPI app + a single static HTML/JS
page that renders **four read-only views** over an existing event-sourced store. No writes, no auth,
localhost only.

## 3. Stack decision (made — push back only with a real reason)
- **FastAPI + uvicorn + one vanilla HTML/JS page.** Rationale: the owner confirmed this grows into
  Phase 8 ("all of the above eventually"); FastAPI is already the specced Phase-8 stack, so the GET
  endpoints are reused, not rewritten. Vanilla JS (fetch + a tiny render) keeps it dependency-light;
  no React/build step for a prototype.
- **Rejected:** Streamlit (fastest to a demo, but a dead-end for Phase 8 — you'd rewrite to get the
  API/WebSocket). Only revisit if the owner decides this is throwaway after all.
- **Dependency hygiene (important):** the core package depends on `jsonschema` only — keep it that
  way. Add `fastapi`/`uvicorn` as an **optional extra**, not a core dep:
  ```toml
  [project.optional-dependencies]
  dashboard = ["fastapi>=0.110", "uvicorn>=0.29"]
  ```
  Install/run with `pip install -e ".[dashboard]"`. The `dashboard` command should fail with a clear
  "install the dashboard extra" message if FastAPI is absent.

## 4. The four views (the entire MVP — do not add a fifth)
| View | Shows | Data source (reuse these — do NOT hand-write SQL) |
|---|---|---|
| **1. Runs list** | task_id · status · #nodes · total tokens · last-event ts | `MemoryStore.tasks()`; per-task status/cost via `reconstruct()` (sum `artifact.provenance.cost.total_tokens`) |
| **2. Run detail** | the DAG (nodes/edges/status) + event timeline + per-node cost | `MemoryStore.reconstruct(task_id)` for status/events; **`DerivedMemory.graph(task_id=…)` for the DAG** (it already emits nodes + `produced_by`/`contains`/`depends_on` edges) |
| **3. Artifact viewer** | one artifact's content + provenance (inputs, model, cost, status) | `MemoryStore.get_artifact(task_id, artifact_id).to_dict()` |
| **4. Recall** | a search box (ranked hits) + the knowledge graph | `DerivedMemory.search(query, task_id=…, agent=…, top=…)` and `DerivedMemory.graph(task_id=…)` |

## 5. Endpoint spec (these become the Phase-8 read API)
All read-only `GET`, JSON, localhost. Mirror the shapes the CLI already emits so they're consistent.
- `GET /api/runs` → `{"tasks": [...]}` (+ optional per-task summary: status, node_count, total_tokens)
- `GET /api/runs/{task_id}` → the `_replay_to_dict(reconstruct(task_id), include_events=True)` shape
  (`task_id`, `status`, `artifacts`, `events`, `failed_node?`)
- `GET /api/runs/{task_id}/graph` → `DerivedMemory.graph(task_id=task_id)` (nodes + edges) — the DAG
- `GET /api/artifacts/{task_id}/{artifact_id}` → `Artifact.to_dict()` (404 if `None`)
- `GET /api/recall?q=…&task_id=…&agent=…&top=…` → `{"query":…, "hits":[...]}` (match `recall` CLI)
- `GET /api/graph?task_id=…` → `DerivedMemory.graph(...)` (whole-store graph when no task_id)
- `GET /` → the static `index.html` (the four views, client-side fetch + render)

**Key reuse references** (don't reinvent):
- `immortals/memory/store.py` — `MemoryStore(db_path)`, `.tasks()`, `.reconstruct()`,
  `.get_artifact()`, `.events_for()`, `.artifacts_for()`; `ReplayResult`, `Artifact.to_dict()`.
- `immortals/memory/derived.py` — `DerivedMemory(store, embedder).search()/.graph()/.neighbors()`.
- `immortals/cli.py` — `_replay_to_dict()` (line ~162), `cmd_replay`/`cmd_recall` for the exact
  JSON shapes and arg semantics to mirror. Factor shared shaping out rather than duplicating it.
- Embedder: use the existing zero-dep default (`HashingEmbedder`) so recall needs no model/network.

## 6. Code location & wiring
- New self-contained module **`immortals/dashboard/`**: `app.py` (FastAPI app factory
  `create_app(db_path)`) + `static/index.html` (+ optional `static/app.js`, `static/style.css`).
  Structure it so Phase-8 write endpoints (`POST /api/tasks`, a WebSocket) slot in later **additively**.
- CLI: add a `dashboard` subcommand in `immortals/cli.py` (`build_parser` + `cmd_dashboard`) that
  resolves `--db` (required), optional `--port` (default e.g. 8765) and `--host` (default `127.0.0.1`),
  then runs uvicorn. Keep it consistent with the existing subcommands' style.
- Package data: ship `static/*` via `[tool.setuptools.package-data]` (like the contracts schemas).

## 7. Definition of Done (coderAS bar)
- `pip install -e ".[dashboard]"` then `python -m immortals dashboard --db <an existing run.db>`
  serves all four views against **real** data, no errors. Core install (no extra) is unaffected.
- **Acceptance run:** point it at the `innovation-digest` store
  (`C:\Code\innovation-digest\.run\run.db`, 4 nodes / 4 artifacts / 22 events) — or a fresh
  `run --backend mock --db …\demo.db` of `scripts/sample_eigen_plan.json` — and confirm: runs list
  shows the task; run-detail renders the DAG + timeline + costs; clicking a node opens its artifact;
  recall returns ranked hits and the graph view renders. Note both data sources in the README.
- **Tests** (`pytest`, keep the suite green): cover the endpoints' **data shaping** (status/cost
  aggregation, graph/recall passthrough, 404 on missing artifact) using an in-memory/temp store —
  **not** the HTML. Use FastAPI's `TestClient`. Don't let dashboard tests fail collection when the
  extra isn't installed (skip/guard the import).
- No new **core** dependency (dashboard extra only). Type-clean and lint-clean to the repo's bar.
- Update `design/handoff.md` (note the dashboard exists as the Phase-8 read-side seed) and the
  kgraph map (a `dashboard` node + edges to `memory/`, `derived`); record provenance.

## 8. Explicitly OUT of scope (defer — surface as follow-ups, don't build)
Submit/run a task · answer check-ins · any write/mutation · auth/login · live-streaming or
WebSockets · always-on-top / bubble window (that's Tauri / Phase 10) · voice · multi-user · fancy
styling or a JS framework/build step · re-implementing reads in raw SQL.

## 9. Risks & guards
- **Scope creep (primary).** The four views + read endpoints are the whole job. A "quick submit
  button" pulls in Phase 7–8 you haven't built → UX-on-sand. Resist; log it as a follow-up.
- **Reinventing reads.** Always go through `MemoryStore`/`DerivedMemory`; if you're writing SQL or
  re-deriving the DAG, you've taken a wrong turn (`DerivedMemory.graph` already gives the DAG).
- **Core-dep bloat.** FastAPI/uvicorn must stay an optional extra; the lean core is a project value.
- **Don't freeze Phase-8 API shape.** These GET routes are a *seed*, not a contract — keep them
  thin and obvious so Phase 8 can extend without fighting the prototype.

## 10. First step (before writing code)
Interview/confirm only the genuinely-open bits: default port, where to ship `static/` for package
vs source-checkout runs (mirror the contracts-schema package-data approach), and whether the owner
wants the acceptance run pointed at the real `innovation-digest` store or a fresh mock run. Then
build §4–6 to the §7 bar. Keep it boring and small.
