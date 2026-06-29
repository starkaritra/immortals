# patrecAS / learnAS — Architecture

> The design spec for the Immortals adaptive-learning module (`patrecAS`, alias *learnAS*),
> controlled by **[AS-027]** (scope), **[AS-012]** (the writer/reader seam), **[AS-006]** (the event
> log it reads), and **[AS-023]** (the Phase-6 derived memory it builds on). The research grounding is
> in `deep-dive.md`; the decisions are `PAT-001…` in `decisions.md`; the build order is `plan.md`.
>
> **Status:** design only — **no code yet**. This file describes the *target* module in the repo's
> declarative, current-state style (as `../design/architecture.md` is the normative spec for the
> orchestrator). Every component below names the **real existing Immortals seam** it attaches to, so
> nothing here invents new substrate.

---

## North star

patrecAS learns the user's/team's characteristics and patterns, maintains a **user/team model**, and
turns that model into **proposed, human-gated, A/B-evaluated adaptations** of the Immortals surface
it is allowed to touch — agent prompts/descriptions, routing, registry manifests, and the roster —
**without ever fine-tuning the (vendor) LLM weights**. It is the *writer* of the team/user model;
managerAS and the worker agents are *readers* (the [AS-012] seam).

**Three invariants** (inherited from Immortals, non-negotiable):
1. **Propose, never apply.** patrecAS only emits proposals; humans approve; the orchestrator gate and
   git enforce it.
2. **Learning lives in data + versioned files, never in weights.** User model = facts; adaptations =
   git diffs to `agents/`/`registry/`. Reversible by construction.
3. **Local-first, append-only, auditable.** Reads the append-only event log; writes only additive
   read-models and proposal artifacts; no third-party data sharing.

---

## Roles

| Actor | Role w.r.t. patrecAS |
|---|---|
| **patrecAS (module)** | deterministic Python: folds the event log into feedback signals, detects roster gaps, clusters unmet needs, builds/serves the user/team model, prepares candidate diffs. Mechanism, like the orchestrator. |
| **patrecAS (agent persona `patrecAS.md` + `registry/v1` manifest)** | the LLM judgment surface: drafts user-model reflections, drafts candidate persona/manifest text, summarizes adaptation rationales. Routed to like any worker. |
| **managerAS** | *reader* of the user/team model at plan time; *requester* of adaptations; surfaces approval prompts. |
| **experimentAS** | evaluates a candidate adaptation (A/B) before adoption — the anti-Goodhart gate. |
| **human (via AS-025 UI / approval gate)** | the only actor that *adopts* an adaptation or *inducts* an agent. |

Mirrors Immortals's split: **deterministic mechanism in Python; LLM judgment confined to a named
agent and explicit escalation points.**

---

## Component map

```
                          ┌──────────────────────────────────────────────────────────┐
                          │                   Immortals substrate                    │
                          │  events (append-only)   facts   artifacts   notes  (SQLite)│
                          │  DerivedMemory: knowledge graph + vector index (AS-023)   │
                          │  Registry.route() / manifests (registry/)   agents/ (.md) │
                          └───────────▲───────────────────────────────▲──────────────┘
                                      │ read-only fold                │ read scores / write proposals
        ┌─────────────────────────────┴────────────┐    ┌─────────────┴─────────────────────────────┐
        │  SignalExtractor (deterministic)          │    │  GapDetector + NeedClusterer (determ.)     │
        │  event log → feedback/v1 read-model       │    │  low route() scores → clustered missing cap │
        └───────────────┬───────────────────────────┘    └─────────────┬───────────────────────────────┘
                        │                                               │
                ┌───────▼─────────┐                            ┌────────▼──────────┐
                │  RewardEstimator │  (per user×agent×cap×tmpl, │  AgentInductor    │ (persona+manifest
                │  + uncertainty   │   with uncertainty)        │  proposer)        │  draft, deduped)
                └───────┬─────────┘                            └────────┬──────────┘
                        │                                               │
                ┌───────▼──────────────────────────────────────────────▼──────────┐
                │  UserTeamModel (writer)   +   AdaptationProposer                  │
                │  facts(agent="patrecAS")  +   prompt/manifest/roster diffs        │
                └───────┬───────────────────────────────────────┬──────────────────┘
                        │ read by managerAS                      │ proposal artifacts
                ┌───────▼─────────┐                      ┌───────▼───────────────────┐
                │   managerAS     │                      │  Governance: experimentAS  │
                │ (plan-time read)│                      │  A/B → human approve → git │
                └─────────────────┘                      │  + agents install / rollback│
                                                         └────────────────────────────┘
```

---

## Core seams patrecAS attaches to (all already exist)

| Seam | Existing API | patrecAS use |
|---|---|---|
| **Event log** | `MemoryStore.events_for(task_id)`, `reconstruct()` | read-only fold → feedback signals. Append-only triggers guarantee patrecAS cannot rewrite history. |
| **Facts** | `MemoryStore.add_fact(... agent, source, supersedes)`, `facts_for(agent=)` | the user/team model is stored here, namespaced `agent="patrecAS"`, updated via `supersedes` (never mutated). |
| **Derived memory** | `DerivedMemory.search()`, `graph()`, `Embedder` seam | semantic retrieval of the user model into the manager's context; `Embedder` reused for need-clustering. |
| **Routing** | `Registry.route(need)` → ranked `{agent, score, reasons}` | gap signal (low top score); bandit re-ranker target (Stage C). |
| **Roster deploy** | repo `agents/` + `registry/`, `immortals agents install`, `config.py` | where an inducted agent's `.md` + manifest land, idempotently and reversibly. |
| **Approval gate** | orchestrator `approval_handler`, `approval_requested`/`granted` events | the human sign-off on every proposal/induction. |
| **Evaluation** | experimentAS manifest (`ab_test`, `experiment_design`, `analysis_report`) | the A/B that must pass before adoption. |

---

## Components

### 1. SignalExtractor (deterministic)
Folds the append-only event log into a **`feedback/v1` read-model** — a derived projection, computed
the same CQRS way `DerivedMemory` is (source of truth = the log; the projection is rebuildable and
can never drift ahead of it). Signals (see `deep-dive.md` §2): plan acceptance, time-to-accept,
re-run/redo count, per-agent failure rate, abandonment, edit distance, cost (guardrail). Pure function
of the log; deterministic; testable with a synthetic event sequence.

### 2. RewardEstimator
Fuses implicit signals (SignalExtractor) with explicit AS-025 thumbs/ratings into a reward estimate
per **(user/team, agent, capability, template)** with an **uncertainty** term (needed by the Stage-C
bandit). Carries a separate, *un-optimized* **guardrail metric** (e.g., human accept on a held-out
sample) to detect Goodhart drift. Zero-dep (closed-form Bayesian/Beta or ridge estimates); no ML
framework.

### 3. UserTeamModel (writer) — the [AS-012] seam
A structured profile of the user/team: preferences, expertise level, working style, recurring goals,
and per-agent performance stats. **Persisted as `facts` namespaced `agent="patrecAS"`**, each with
`source` provenance and updated via `supersedes` (additive, never in-place — the R5 anti-poisoning
pattern). Served to managerAS two ways: structured (`facts_for(agent="patrecAS")`) and semantic
(`DerivedMemory.search(query, agent="patrecAS")`). This *is* the writer side of [AS-012]; managerAS is
the reader and does **not** own the learning.

### 4. AdaptationProposer
Generates candidate **diffs** to the controllable surface, each as a typed **proposal artifact**
(`adaptation_proposal/v1`) — never applied directly:
- **persona diff** — edit to a `<name>AS.md` body (clarify instructions, add a learned convention).
- **manifest diff** — edit to `registry/v1` `when_to_use`/`summary`/`capabilities` to improve routing.
- **routing-policy update** — bandit parameters (Stage C).
Generation uses the reflective prompt-optimization pattern (DSPy/OPRO/GEPA, `deep-dive.md` §3) but the
*proposal* is the output, not an applied change.

### 5. GapDetector + NeedClusterer + AgentInductor (Stage E)
- **GapDetector** folds the log for needs whose best `Registry.route()` score is below threshold
  (or repeated escalations / "no suitable agent").
- **NeedClusterer** embeds unmet `need` strings via the Phase-6 `Embedder` and clusters by cosine
  threshold (zero-dep) to confirm a *recurring* gap.
- **AgentInductor** drafts a candidate `<name>AS.md` persona (LOCKED naming) + a `registry/v1`
  manifest (schema-validated by the existing `AgentManifest.from_dict`), deduped against existing
  manifests by capability similarity. Output is a proposal; adoption is human-gated then
  `agents install`. Because routing is registry-driven [AS-004], the new agent is routable with **no
  code change**.

### 6. Governance
The adoption path for *every* proposal and induction: experimentAS A/B (must beat control on the
reward proxy *and* not regress the guardrail metric) → human approval (orchestrator gate / AS-025) →
git commit of the diff → `agents install` → continued measurement. Includes **reset/opt-out**
(`patrecAS reset` drops the user model + reverts learned diffs) and **rollback** (revert the git diff).

---

## Data flow (end to end)

1. **Observe.** Runs execute; the orchestrator appends `event/v1` records (unchanged).
2. **Extract.** SignalExtractor folds the log → `feedback/v1`; RewardEstimator updates estimates.
3. **Model.** UserTeamModel writes/updates `facts(agent="patrecAS")` with provenance + supersedes.
4. **Serve.** managerAS retrieves the user model at plan time (semantic + structured) and plans
   accordingly (Stage A — pure read, no risk).
5. **Propose.** On a trigger (drift, a roster gap, a manager request), patrecAS emits an
   `adaptation_proposal/v1` (prompt/manifest diff) or an `agent_induction/v1` (persona + manifest).
6. **Evaluate.** experimentAS A/Bs the proposal over replayable tasks (the event log makes runs
   reproducible); offline counterfactual estimation (bandit replay, `deep-dive.md` §4.2) is used
   before any online exploration.
7. **Approve & apply.** Human approves; the diff is committed (git) and synced (`agents install`);
   the change is now live, versioned, and reversible.
8. **Audit.** Every step is an event in the append-only log; the whole adaptation history is
   `reconstruct`-able.

The loop is **closed but human-gated**: patrecAS never self-applies; the human is the actuator.

---

## Contracts (proposed new schemas, validated at every seam)

These follow the existing versioned-JSON + `validate(obj, "<schema>")` convention. They are additive;
no existing schema changes.

- **`feedback/v1`** — a derived signal record: `{user, agent, capability, template, signal_type,
  value, uncertainty, source_events:[event_id…], ts}`. A read-model projection of the event log.
- **`user_model/v1`** — the served view of the team/user model (assembled from `patrecAS` facts):
  `{user, preferences, expertise, style, goals, agent_stats, provenance, version}`. The [AS-012] seam
  contract between patrecAS (writer) and managerAS (reader).
- **`adaptation_proposal/v1`** — `{target_kind: persona|manifest|routing, target_id, diff,
  rationale, expected_reward_delta, evidence:[feedback…], requires_approval:true}`.
- **`agent_induction/v1`** — `{proposed_name:"<name>AS", persona_md, manifest:registry/v1,
  gap_evidence:[need_cluster…], dedupe_report, requires_approval:true}`.

---

## Storage & access

- **Substrate — reuse, don't add.** Everything lives in the existing local SQLite DB: the user model
  in `facts`, the derived feedback in a new read-model table built the same way `DerivedMemory` builds
  its graph/embeddings (rebuildable from source). **Zero new dependencies; local-first; no egress.**
- **Embedding — reuse the seam.** Need-clustering and user-model retrieval use the pluggable
  `Embedder` (zero-dep `HashingEmbedder` default; `sqlite-vec`/real model is the named future backend
  behind the same seam, exactly as [AS-023] framed it).
- **Access — MCP/CLI, consistent with the suite.** patrecAS exposes reads/proposals via the same
  MCP + `immortals` CLI surface (e.g. `patrecAS model`, `patrecAS propose`, `patrecAS induct`,
  `patrecAS reset`), so managerAS and the human use one uniform interface.

---

## How managerAS consumes the model

At plan time managerAS (the only user-facing agent) issues a structured + semantic read of the
`user_model/v1` view and folds it into its planning context — e.g. "this user prefers terse outputs,
high rigor, and has rejected experimentAS-heavy plans before; prior coderAS work on this repo
succeeded." managerAS keeps owning *orchestration*; patrecAS owns *learning*. If managerAS detects a
persistent routing miss or a capability gap during planning, it can *request* an adaptation/induction
proposal from patrecAS — but cannot adopt one itself.

---

## Security (inherited + extended)

- **Learned data is untrusted data.** Signals/feedback/artifacts patrecAS learns from are *data*,
  never instructions — the [AS-003] containment rule, extended to defend indirect prompt injection via
  learned content (`deep-dive.md` §3.2, [Greshake 2023]).
- **Anti-Goodhart by gate.** No proposal is adopted without an experimentAS A/B win on the reward
  proxy *and* no regression on the un-optimized guardrail metric ([Pan et al. 2022]).
- **Reversibility.** Every adaptation is a git diff; rollback is one revert. Induction never bypasses
  the human gate or the `agents install` path.
- **Privacy.** Behavioural data is local-first; learning is off by default until opted in; `reset`
  purges the user model and reverts learned diffs.

---

## What is explicitly out of scope (and why)

- **Fine-tuning the Copilot/planner LLM (true RLHF/DPO/PPO).** No weight access under Backend A
  (`deep-dive.md` §1). Reopens only with a self-hosted planner (Backend C) — Stage D, research-only.
- **Unconstrained self-modification** (Gödel-machine-style auto-rewrite without a human gate). The
  archive + empirical-validation + human-approval pattern is adopted instead ([DGM, 2025]).
- **Auto-applying any change.** Forbidden by the propose-not-apply invariant.
