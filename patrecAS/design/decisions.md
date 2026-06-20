# patrecAS / learnAS — Decisions (ADR-style)

> Module-local decision log for `patrecAS` (alias *learnAS*). Anchors are `PAT-001…`, append-only:
> stable anchors; when superseded, keep the anchor and change the title. These sit *under* the
> top-level AgentSuite decisions — especially **[AS-027]** (controlling), **[AS-012]**, **[AS-006]**,
> **[AS-023]**, **[AS-024]**, **[AS-025]** — and never contradict them. Research grounding for each
> decision is in `deep-dive.md`; the architecture is in `architecture.md`.

---

### [PAT-001] "RLHF-type" is reframed as preference-based adaptation of the controllable surface
- **Status:** accepted (research-validated).
- **Context:** the owner asked for an "RLHF-type learning model." Literal RLHF/DPO/PPO update the
  weights of a model you own; AgentSuite invokes the Copilot planner as a black-box `copilot` process
  (Backend A) and owns no weights (`deep-dive.md` §1).
- **Decision:** patrecAS performs **preference-based adaptation over the surface AgentSuite controls**
  — agent prompts/descriptions, routing, registry manifests, and the roster — **not** gradient RLHF on
  the LLM. The *reward-modeling concept* from RLHF is retained and reused (the learned scorer in
  PAT-004); the *weight-update mechanism* is deferred to PAT-009 behind a self-hosted-planner
  contingency.
- **Options considered:**
  - *(chosen)* Black-box, in-context + file-level adaptation — pros: feasible today, local-first,
    reversible, deterministic-testable; cons: cannot change the model's intrinsic abilities.
  - True RLHF/DPO on the planner — pros: most expressive; cons: impossible without owning weights;
    heavy, non-deterministic, data-egress risk. Out of scope until Backend C.
- **Evidence:** Voyager learns via blackbox queries with no fine-tuning [arXiv:2305.16291]; GEPA shows
  language-space adaptation beating RL with ~35× fewer rollouts [arXiv:2507.19457]; InstructGPT/DPO
  confirm the weight-update requirement [arXiv:2203.02155, 2305.18290]. (All *verified* in
  `deep-dive.md`.)
- **Consequences:** the whole module is built on retrieval + versioned file diffs + a discrete-action
  reward model, never on a training loop over the vendor LLM.

---

### [PAT-002] Staged approach A → E → B → C → D (sequence locked, per [AS-027])
- **Status:** accepted.
- **Decision:** build in the [AS-027] order:
  - **A — Retrieval personalization** (MVP): a user/team model as facts + vectors, read by managerAS.
  - **E — New-agent induction**: detect a roster gap → propose persona + manifest → human-approve →
    `agents install`.
  - **B — Approved prompt/manifest diffs**: versioned, A/B-evaluated edits to personas/manifests.
  - **C — Contextual-bandit routing**: a learned-reward re-ranker over `Registry.route()`.
  - **D — DPO/weight-level RLHF**: research-only, contingent on a self-hosted planner.
- **Rationale:** strict increasing order of *risk and machinery*. A is pure read (no risk). E is high
  value/low friction because routing is registry-driven [AS-004]. B introduces file edits behind the
  A/B gate. C introduces online learning (highest Goodhart risk) only after the gate and offline
  evaluation exist. D is gated on a different architecture entirely.
- **Links:** [AS-027], `plan.md`.

---

### [PAT-003] Adaptations are proposals: propose-not-apply, git-versioned, A/B-gated, reversible
- **Status:** accepted (non-negotiable safety rail, from [AS-027]).
- **Decision:** patrecAS **only emits proposals** (`adaptation_proposal/v1`). Adoption requires: an
  experimentAS A/B win on the reward proxy **and** no regression on an un-optimized guardrail metric →
  human approval (orchestrator gate / AS-025) → git commit of the diff → `agentsuite agents install`.
  Every adaptation is a reviewable, reversible git diff; rollback is one revert.
- **Rationale:** text/prompt optimizers reliably overfit metrics (Goodhart), drift, and can be
  hijacked by injected learned text (`deep-dive.md` §3.2). The gate + versioning + reversibility make
  the module *safe by construction*.
- **Evidence:** reward-misspecification phase transitions [arXiv:2201.03544]; indirect prompt
  injection [arXiv:2302.12173]; DGM's archive+empirical-validation discipline over unconstrained
  self-rewrite [arXiv:2505.22954]. (All *verified*.)
- **Links:** [AS-003], [AS-005], [AS-024], experimentAS manifest.

---

### [PAT-004] Routing adaptation is a contextual bandit with offline evaluation first
- **Status:** accepted (scheduled Stage C).
- **Decision:** model "which agent / which template for this need" as a **contextual bandit**
  (LinUCB-style UCB or Thompson sampling) that **re-ranks** `Registry.route()` candidates using the
  RewardEstimator + per-arm uncertainty. The deterministic lexical scorer stays as the cold-start
  prior and fallback. **Mandatory:** build the **offline replay / inverse-propensity estimator first**
  and require a predicted win on logged data *before* enabling any capped online exploration.
- **Rationale:** routing is discrete-action, immediate-feedback, no long horizon — the textbook bandit
  setting; LinUCB also gives an unbiased offline evaluator over logged data, and AgentSuite's event
  log *is* such a log with replayable runs.
- **Evidence:** LinUCB + offline policy evaluation [arXiv:1003.0146, *verified*]; bandit selection
  already used inside prompt optimization (APO) [arXiv:2305.03495, *verified*].
- **Consequences:** highest-machinery, highest-Goodhart lever → deliberately last before D, behind the
  PAT-003 gate.

---

### [PAT-005] Reward signal = event-log implicit feedback fused with AS-025 explicit feedback
- **Status:** accepted.
- **Decision:** a **`feedback/v1` read-model** is computed by **folding the append-only event log**
  (never mutating it): plan acceptance (`approval_granted` vs denied), time-to-accept
  (`approval_granted − approval_requested`), re-run/redo counts (`--from`/`--to`, repeated
  `node_started`), per-agent `node_failed` rate, abandonment (no `run_completed`), edit distance, and
  cost (guardrail). Fused with explicit AS-025 thumbs/ratings (KTO-style binary signal) into a reward
  estimate **with uncertainty** and a separate **un-optimized guardrail metric**.
- **Rationale:** the telemetry already exists; implicit feedback is rich but biased/noisy, so it must
  carry uncertainty and be paired with an unoptimized guardrail to detect Goodhart drift.
- **Evidence:** KTO aligns from binary desirable/undesirable signals [arXiv:2402.01306, *verified*];
  reward-misspecification risk [arXiv:2201.03544, *verified*].
- **Links:** [AS-006] event log, [AS-018] cost, [AS-025] UI.

---

### [PAT-006] New-agent induction reuses the registry's "routable with no code change" property
- **Status:** accepted (Stage E).
- **Decision:** the induction pipeline = **GapDetector** (repeated low `Registry.route()` top scores /
  escalations) → **NeedClusterer** (embed unmet `need` strings via the Phase-6 `Embedder`, cosine
  cluster) → **AgentInductor** (draft `<name>AS.md` persona + schema-validated `registry/v1` manifest,
  deduped against existing manifests) → **human approval** → **`agentsuite agents install`**. The new
  agent becomes routable with **no code change** because routing is registry-driven [AS-004].
- **Rationale:** the research shows automatic agent/role generation works (ADAS, AutoAgents) and the
  AgentSuite registry design makes it unusually cheap and safe to add an agent.
- **Evidence:** ADAS meta-agent invents transferable agents [arXiv:2408.08435, *verified*]; AutoAgents
  generates+coordinates roles with an observer/reflection step [arXiv:2309.17288, *verified*].
- **Safeguards:** dedupe vs existing capabilities; an experimentAS evaluation that the new agent
  actually *wins* the clustered need; never bypass the human gate; LOCKED `<name>AS.md` naming
  ([AS-024]).
- **Links:** [AS-004], [AS-024], `route()` in `registry/loader.py`.

---

### [PAT-007] Privacy/governance: local-first, off-by-default, reset/opt-out, full audit
- **Status:** accepted (non-negotiable).
- **Decision:** behavioural learning is **off by default** until the user opts in; all behavioural data
  stays in the local SQLite DB (no third-party sharing; HashingEmbedder default avoids API-embedding
  egress); a `patrecAS reset`/opt-out drops the user model and reverts learned diffs; every adaptation
  decision is logged as an event and is `reconstruct`-able.
- **Rationale:** behavioural/preference data is sensitive; the controls already exist in AgentSuite
  (local-first [AS-007], append-only audit [AS-006], injection containment [AS-003]) and patrecAS
  inherits them plus reset/opt-out.
- **Links:** [AS-006], [AS-007], [AS-003].

---

### [PAT-008] Storage: reuse the existing SQLite substrate + facts + Embedder seam (zero new deps)
- **Status:** accepted.
- **Decision:** no new datastore and no new third-party dependency. The user/team model lives in the
  existing `facts` table namespaced `agent="patrecAS"` (with `source` + `supersedes`); the
  `feedback/v1` read-model is a rebuildable projection built the same CQRS way as `DerivedMemory`;
  embeddings reuse the pluggable `Embedder` (zero-dep default, `sqlite-vec`/real model the named future
  backend). New schemas (`feedback/v1`, `user_model/v1`, `adaptation_proposal/v1`, `agent_induction/v1`)
  are additive and validated via the existing `validate()` convention.
- **Options considered:** a separate store / a vector DB now — rejected: violates the zero-dep,
  local-first, deterministic-test posture and duplicates Phase-6 substrate.
- **Rationale:** matches [AS-023]'s pluggable-seam philosophy; keeps reproducible tests and offline
  operation.
- **Links:** [AS-023], `memory/store.py`, `memory/derived.py`, `memory/embedding.py`.

---

### [PAT-009] DPO/weight-level RLHF is research-only, contingent on a self-hosted planner
- **Status:** proposed (deferred — Stage D).
- **Decision:** true DPO/RLHF over a planner model is **not** built while the planner is a black-box
  vendor LLM. It reopens only if AgentSuite adopts a **self-hosted/ownable planner** (Backend C
  direction). At that point the reward model already built for PAT-004 supplies the preference signal,
  and DPO (simpler/stabler than PPO) is the preferred recipe.
- **Rationale:** keeps a credible long-term research path without blocking the feasible near-term
  stages or compromising the local-first/zero-dep posture.
- **Evidence:** DPO removes the RL loop and reward-model step, but still fine-tunes weights
  [arXiv:2305.18290, *verified*].
- **Links:** [AS-025] (manager-as-driver / Backend C), PAT-001, PAT-004.

---

### [PAT-010] patrecAS is both a Python module and a `patrecAS.md` agent
- **Status:** accepted.
- **Decision:** the **deterministic** parts (signal extraction, gap detection, clustering, reward
  estimation, diff assembly, governance plumbing) are Python *mechanism* (like the orchestrator); the
  **judgment** parts (drafting user-model reflections, drafting candidate persona/manifest text,
  writing adaptation rationales) live in a `patrecAS.md` persona with a `registry/v1` manifest so
  managerAS can route "learn my preferences / adapt the suite / we need a new kind of agent" tasks to
  it.
- **Rationale:** mirrors AgentSuite's core split (determinism where it counts; LLM judgment confined to
  a named agent) and makes patrecAS itself a first-class, routable suite member under the LOCKED
  `<name>AS.md` convention.
- **Links:** [AS-001], [AS-024], `architecture.md` (Roles).
