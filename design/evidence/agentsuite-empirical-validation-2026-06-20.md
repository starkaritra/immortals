# Immortals — Empirical Validation Record

**Run ID:** `innovation-digest-2026-06-20`
**Date:** 2026-06-20 (Asia/Kolkata)
**Author/operator:** managerAS (user: t-aritradas)
**Purpose:** Serve as empirical, reproducible proof that the Immortals mechanism
(managerAS → `plan/v1` → registry routing → deterministic orchestrator → headless worker
agents → seam-validated `artifact/v1` → quality gate → synthesis) works end-to-end on a
real, non-trivial task, not a toy/mock.

> This is a living record. Sections 1–6 are captured **before** execution (intake, live
> registry/routing checks, the emitted plan). Section 7+ are filled **after** the orchestrator
> run with the actual results, costs, and produced artifacts.

---

## 0. Environment (provenance)

| Field | Value |
|---|---|
| Immortals repo | `C:\Code\Immortals` @ git `78c0e7e` |
| Orchestrator backend | `copilot` (Backend A — headless `copilot --agent … -p … --output-format json`) |
| Copilot CLI | `1.0.64-1` |
| Python (venv) | `3.12.10` (`.venv\Scripts\python.exe`) |
| Build workspace | `C:\Code\innovation-digest` (fresh dir; all worker file writes land here) |
| Plan file | `C:\Code\innovation-digest\plan.v1.json` |
| Event store (DB) | `C:\Code\innovation-digest\.run\run.db` (event-sourced; enables `--resume`) |
| OS | Windows_NT |

---

## 1. Task under test (the real workload)

Build a **weekly research-innovation digest** product:

- A **Chrome MV3 extension** lets the user pick topics/domains of interest, add RSS feeds, and
  set their email (config UI + "view latest digest").
- A **Cloudflare Worker** (Cron Trigger, weekly) reads that config from Workers KV, fetches new
  items from **arXiv + Semantic Scholar + RSS**, dedupes, summarizes each via the **Gemini**
  free API (title + 1 paragraph: *what it is / why it matters / relevance* + follow-up links),
  groups by topic, and **emails** a consolidated digest via a free provider.

Architecture was chosen consultatively with the user (intake): extension-only → free serverless
backend; LLM = Gemini free; email = free provider; cadence = **weekly**.

This is a genuine multi-file software build with cross-component contracts (extension ↔ Worker
API) — chosen specifically because it is hard enough to exercise real routing, dependencies,
shared-workspace file hand-off, and the approval gate.

---

## 2. Pre-registered hypothesis & success criteria

**H1 (mechanism works):** managerAS can emit a schema-valid `plan/v1` DAG, the orchestrator
routes each node to a registry-selected specialist, executes them in dependency order as real
headless `copilot` subprocesses, validates every seam to `artifact/v1`, and persists an
event-sourced log — with no manual stitching between nodes.

**Pre-registered pass criteria (decided before the run):**

1. **PC1 — Plan validity:** the emitted plan validates against
   `immortals/contracts/schemas/plan.v1.json`.
2. **PC2 — Live routing:** the capability registry (not hardcoded logic) ranks the intended
   agent first for each sub-task need. *(captured in §4)*
3. **PC3 — Real execution:** every node runs as an actual `copilot --agent … -p …` subprocess
   (non-mock backend) and returns a seam-valid `artifact/v1` with `status="ok"`.
4. **PC4 — Dependency ordering:** `stress-test` runs after `research-sources`; both `build-*`
   nodes run after their upstreams; `build-extension` runs after `build-worker`.
5. **PC5 — Artifact hand-off:** upstream artifacts are passed to downstream nodes as fenced
   data, and the shared workspace lets `build-extension` read `build-worker`'s files.
6. **PC6 — Approval gate:** the two `approval: required` coderAS nodes are gated and only run
   after an explicit grant (`--approve` issued post user sign-off).
7. **PC7 — Tangible output:** real files are produced under `C:\Code\innovation-digest\worker`
   and `…\extension`.
8. **PC8 — Accounting:** the run reports per-node token/cost usage and an event trail
   reconstructable via `immortals replay`.

**Falsification:** any of PC1–PC8 failing (e.g., a node silently skipped, a seam validation
error, mock backend used, or zero files produced) falsifies H1 for this run and is recorded
verbatim in §8 (no cherry-picking).

---

## 3. Live check A — registry is real and populated

Command:

```powershell
.\.venv\Scripts\python.exe -m immortals agents
```

Result: 9 agents returned with capabilities/consumes/produces/approval_default/cost_hint
(coderAS, discussAS, experimentAS, paperAS, patentAS, prepAS, presentAS, researchAS, teachAS).
`coderAS.approval_default = "required"`, `discussAS = "none"`, `researchAS = "none"`. ✅

---

## 4. Live check B — routing (PC2)

Three real `route` queries (router is keyword/capability scoring over `registry/v1` manifests,
not hardcoded):

| Need (free text) | Top pick | Why |
|---|---|---|
| "research & verify best free APIs/RSS feeds … CF cron, Gemini, email integration" | **researchAS** | `text~research` (coderAS/experimentAS tie on `text~verify`; researchAS is the correct capability match) |
| "implement a Chrome MV3 extension + Cloudflare Worker backend …" | **coderAS** (only candidate) | `text~implement` |
| "stress-test the architecture for blind spots, CORS, rate limits, free-tier pitfalls" | **discussAS** (score 8) | `cap~stress, cap~test, text~blind/spots/stress/test` |

Routing confirms the intended specialists are registry-selected for each sub-task. ✅

---

## 5. Live check C — CLI & seam contracts exist

- `immortals` CLI exposes `run / replay / agents / route / recall / memory`.
- `run` supports the guardrails used here: `--workspace`, `--db`, `--approve`,
  `--enforce-approvals`, `--max-tokens`, `--max-seconds`, `--max-nodes`, `--max-workers`,
  `--resume`, `--from/--to`, `--events`, `--pretty`.
- Plan schema `plan.v1.json` requires `schema/task_id/goal/nodes`; nodes require
  `id/agent/prompt/produces` with optional `inputs/depends_on/success_criteria/reversibility/
  approval/budget`.
- Backend `copilot_backend.py` runs each node as
  `copilot --agent <a> -p <prompt> --output-format json --no-ask-user --allow-all-tools
  [--add-dir <workspace>]`, with `cwd = workspace`, folds JSONL → `artifact/v1`, and records
  `provenance.cost.total_tokens` from real usage. (Confirms PC3 backend is non-mock.)

---

## 6. The emitted plan/v1 (PC1, PC4)

File: `C:\Code\innovation-digest\plan.v1.json` (4 nodes, 3 specialists). DAG:

```
research-sources (researchAS)
        │
        ▼
   stress-test (discussAS)
        │
        ├──────────────┐
        ▼              │
  build-worker (coderAS, approval:required)
        │
        ▼
 build-extension (coderAS, approval:required)   [reads ./worker via shared workspace]
```

Schema validation result: _(captured at execution time — see §7)_.

---

## 7. Execution log & results

### Stage 1 — upstream (research + stress-test), executed 2026-06-20 14:28–14:38 UTC

Run staged at the user's request (review the cheap nodes before approving the costly builds):

```powershell
.\.venv\Scripts\python.exe -m immortals run `
  --plan-file C:\Code\innovation-digest\plan.v1.json `
  --backend copilot --workspace C:\Code\innovation-digest `
  --db C:\Code\innovation-digest\.run\run.db `
  --to stress-test --events --pretty
```

(`--to stress-test` selects that node + its upstream → `research-sources`, `stress-test`.)

| Node | Agent | Status | Model | Output tokens | Premium reqs | Wall time | Artifact id |
|---|---|---|---|---|---|---|---|
| research-sources | researchAS | **ok** | claude-opus-4.8 | 21,721 | 15 | ~6m 02s | `research_report` |
| stress-test | discussAS | **ok** | claude-opus-4.8 | 12,767 | 15 | ~4m 12s | `design_critique` |
| build-worker | coderAS | _not yet run_ | | | | | worker_impl |
| build-extension | coderAS | _not yet run_ | | | | | extension_impl |

**Event log (clean, ordered, event-sourced):** `plan_validated` → `decision(partial_run: to=stress-test, selected=[research-sources, stress-test])` → `node_started(research-sources/researchAS)` → `artifact_written(research_report)` → `node_completed` → `node_started(stress-test/discussAS)` → `artifact_written(design_critique)` → `node_completed` → `run_completed(artifacts=[design_critique, research_report])`. 9 events, 2 artifacts persisted.

**Dependency ordering observed:** research-sources ran 14:28:34→14:34:36, then stress-test ran 14:34:36→14:38:49 — stress-test did not start until its upstream completed. ✅

**Files produced under `C:\Code\innovation-digest`:**
- `integration-brief.WRID.md` (~20.8 KB) — researchAS's cited integration brief (arXiv, Semantic Scholar, RSS, CF cron+KV, Gemini, email providers; every claim cites a primary source, unverified items tagged `[FLAG]`).
- `design-critique.md` (~16.5 KB) — discussAS's red-team review: 11 ranked issues + **12 must-change decisions** + risk/assumption ledger + self-audit.

**Substantive proof the work is real (not mock):** discussAS independently identified a **CRITICAL** architectural flaw — summarizing one item per Gemini call collides with Cloudflare Free's **50-subrequest/invocation** ceiling, aborting the digest mid-run — and prescribed batched summarization + run caps + cold-start seeding. It also caught the Resend domain-verification trap (→ default to Brevo), the MV3 static-`host_permissions` vs runtime Worker-URL problem, secret-in-header (not URL), and KV single-writer/lock/prune. These are correct, non-obvious, and materially change the build.

### Stage 2 — build nodes (coderAS ×2), executed 2026-06-20 14:53–15:25 UTC

Resumed from the DB (upstream artifacts loaded from the store), gated nodes auto-approved:

```powershell
.\.venv\Scripts\python.exe -m immortals run `
  --plan-file C:\Code\innovation-digest\plan.v1.json `
  --backend copilot --workspace C:\Code\innovation-digest `
  --db C:\Code\innovation-digest\.run\run.db `
  --from build-worker --resume --approve --events --pretty
```

**Approval gate (PC6) — observed for BOTH build nodes:**
`approval_requested(build-worker/coderAS)` → `approval_granted` → `node_started` … then identically for `build-extension`. The gate is registry-true: coderAS's `approval_default="required"` was honoured; nodes ran only after the grant.

| Node | Agent | Status | Model | Output tokens | Wall time | Verification (headless) |
|---|---|---|---|---|---|---|
| build-worker | coderAS | **ok** | claude-opus-4.8 | 74,376 | ~20m 25s (14:53:09→15:13:34) | `npm test` **55/55 pass**, `tsc --noEmit` strict clean, `wrangler deploy --dry-run` clean (34.79 KiB bundle) |
| build-extension | coderAS | **ok** | claude-opus-4.8 | 46,676 | ~12m 03s (15:13:34→15:25:37) | `npm test` **23/23 pass**, manifest valid, live API-client integration test vs a mock of the Worker contract |

**Artifact hand-off across nodes (PC5) — verified concretely:**
- discussAS's critique cites researchAS's brief as ground truth (consumed `research_report`).
- build-worker consumed `research_report` + `design_critique` and its report states "all 12 design-critique must-change decisions applied."
- build-extension consumed `worker_impl` AND read `./worker`'s code+README in the shared workspace to match the HTTP API contract and Bearer-auth exactly — cross-component contract held with no manual stitching.

**Files produced (PC7):**
- `./worker` — Cloudflare Worker: `src/{index,digest,config,auth,budget,dedupe,summarize,render}.ts`, `src/sources/{arxiv,semanticscholar,rss,xml}.ts`, `src/email/index.ts`, `wrangler.toml`, `README.md`, `.dev.vars.example`, 8 vitest suites (55 tests).
- `./extension` — MV3 extension: `manifest.json`, `src/{api,storage,options.js,popup.js}` + `options/popup .html/.css`, `icons/`, `README.md`, 2 node:test suites (23 tests).

**Full run reconstructable (PC8):** `immortals replay --db …\run.db --task-id innovation-digest-2026-06-20 --pretty` → `status: completed` with all four seam-valid `artifact/v1` (each carrying `provenance.cost`), produced purely by folding the 22-event log.

### Run totals

| Metric | Value |
|---|---|
| Nodes executed | 4/4 ok (researchAS, discussAS, coderAS×2) |
| Output tokens (sum) | **155,540** (21,721 + 12,767 + 74,376 + 46,676) |
| Backend | copilot (real headless subprocesses), model claude-opus-4.8 |
| Agent compute wall time | ~42 min across the 4 nodes |
| Events logged | 22 (event-sourced, ordered) |
| Tests passing in delivered code | worker 55/55 + extension 23/23 = **78/78** |
| Manual stitching of intermediate outputs | **none** — all hand-off via artifacts + shared workspace |

---

## 8. Verdict against pre-registered criteria  *(filled after the run)*

| Criterion | Result | Evidence |
|---|---|---|
| PC1 Plan validity | ✅ | §6 — validates against `plan.v1.json` (4 nodes, 3 edges) |
| PC2 Live routing | ✅ | §4 — researchAS / discussAS / coderAS registry-ranked for their needs |
| PC3 Real (non-mock) execution | ✅ | §7 — all 4 nodes ran as `copilot`/claude-opus-4.8 subprocesses; real token + premium-request usage per node |
| PC4 Dependency ordering | ✅ | §7 — research→stress-test→build-worker→build-extension; each started only after its upstream `node_completed` |
| PC5 Artifact hand-off | ✅ | §7 — critique cites brief; build-worker applied all 12 MCDs; build-extension matched the Worker contract via shared workspace |
| PC6 Approval gate | ✅ | §7 Stage 2 — `approval_requested`→`approval_granted`→`node_started` for both coderAS nodes (registry `approval_default=required` honoured) |
| PC7 Tangible output | ✅ | §7 — runnable `./worker` + `./extension` projects on disk |
| PC8 Accounting/event log | ✅ | §7 — 22-event ordered log + per-node `provenance.cost`; full run rebuilt via `immortals replay` |

**Overall verdict:** **PASS (8/8 pre-registered criteria).** The Immortals mechanism executed a real, non-trivial, cross-component software build end-to-end: managerAS emitted a schema-valid `plan/v1`; the orchestrator routed each node to a registry-selected specialist; ran them as real headless `copilot` subprocesses in correct dependency order; enforced the approval gate on the two coderAS nodes; passed artifacts between nodes (and shared the workspace so the extension matched the Worker's contract) with **no manual stitching**; validated every seam to `artifact/v1`; accounted token/premium cost per node; and persisted a replayable event log. The delivered code is self-verified (78/78 tests pass, type-clean, deploy-dry-run clean). H1 is **corroborated** for this run.

**Non-cherry-picked observations / minor wrinkles (recorded for honesty):**
- researchAS coined the acronym **WRID** and named its brief `integration-brief.WRID.md` (the literal token "WRID" in the filename is intentional, not a templating bug).
- `premium_requests` reported as `15` for every node — appears to be a per-session metric/cap surfaced identically rather than a strict per-node count; output-token accounting is the reliable cost signal.
- The two `build-*` nodes are reversible file-generation, yet correctly still required approval (coderAS manifest floor) — gate behaved conservatively, as designed.

**Threats to validity / caveats:** headless coderAS cannot truly load a Chrome extension or
deploy a Cloudflare Worker in-process, so "verify" at the build nodes is limited to
build/lint/unit-tests; final load-unpacked + `wrangler deploy` are manual (documented in each
component README). This does not affect H1 (mechanism), only the runnability ceiling of a single
headless build pass.

---

## 9. Reproduction

```powershell
cd C:\Code\Immortals
.\.venv\Scripts\python.exe -m immortals agents                      # registry
.\.venv\Scripts\python.exe -m immortals route --need "<sub-task>" --pretty
.\.venv\Scripts\python.exe -m immortals run --plan-file C:\Code\innovation-digest\plan.v1.json `
    --backend copilot --workspace C:\Code\innovation-digest `
    --db C:\Code\innovation-digest\.run\run.db --approve --pretty
.\.venv\Scripts\python.exe -m immortals replay --db C:\Code\innovation-digest\.run\run.db --pretty
```

---

## 10. Conclusion — synthesis delivered to the user (2026-06-20)

> Verbatim record of the final synthesis managerAS delivered at run close, kept here so the
> evidence doc is self-contained.

**Bottom line.** The weekly research-innovation digest is built and self-verified, and the
Immortals mechanism passed **8/8 pre-registered criteria**.

**What exists on disk (`C:\Code\innovation-digest`):**
- **`./worker`** — Cloudflare Worker engine: weekly cron, KV config+dedupe, arXiv + Semantic
  Scholar + RSS fetchers, **batched** Gemini summarizer (title + 1-paragraph *what/why/relevance*
  + links), topic-grouped HTML+text email (Brevo default), authenticated HTTP API. **55/55 tests
  pass, type-clean, `wrangler --dry-run` clean.**
- **`./extension`** — MV3 Chrome extension: options page (topics/RSS/email/Worker-URL/secret/
  schedule), popup digest viewer + "Generate now", least-privilege perms. **23/23 tests pass.**
- Both READMEs document the remaining manual steps (free Cloudflare/Gemini/Brevo accounts, set
  secrets, `wrangler deploy`, load-unpacked).

**Immortals — verified working (the transparency goal):**

| Claim | How it was proven |
|---|---|
| Plan is a real typed contract | schema-validated `plan/v1` (4 nodes) |
| Registry routing, not hardcoded | live `route` queries → researchAS / discussAS / coderAS |
| Real agents, not mock | 4 headless `copilot`/claude-opus-4.8 subprocesses, **155,540 output tokens** total |
| Correct DAG ordering | research→critique→worker→extension, each after upstream `node_completed` |
| Cross-node hand-off, no stitching | critique cited the brief; worker applied all 12 critique decisions; extension matched the worker's API contract via the shared workspace |
| Approval gate is real | `approval_requested→granted→started` logged for both coderAS nodes |
| Auditable | 22-event log, per-node cost, full run rebuilt via `immortals replay` |

**Proof it's not theater:** discussAS independently caught a CRITICAL flaw (per-item Gemini calls
would blow Cloudflare's 50-subrequest cap and abort the digest) → coderAS implemented batched
summarization to fix it. The pipeline produced **better** architecture than the naive plan.

**Honest caveats:**
- Headless agents can't load a real Chrome extension or deploy to Cloudflare — final
  `load-unpacked` + `wrangler deploy` are manual (READMEs cover it). "Verified" = build /
  typecheck / tests / dry-run.
- Requires three free-tier accounts (Cloudflare, Google AI Studio for Gemini, Brevo).
- `premium_requests` logged as 15/node looks like a per-session metric, not a strict per-node
  count.

**After-action review (LEARN step):** the one process miss this run was a long communication
gap while the orchestrator ran as a blocking call, plus not auto-summarizing artifacts at the
upstream checkpoint. Both were corrected mid-run — for the build stage managerAS ran the
orchestrator async and narrated at every node transition (start / completion / tokens / files
landed) by polling the event DB, and auto-summarized each artifact at the checkpoint. These are
now the default behaviours for future runs.
