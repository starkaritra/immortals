# patrecAS / learnAS — Research & Landscape Deep-Dive

> **What this file is.** A grounded literature/landscape survey for the AgentSuite adaptive-learning
> module (`patrecAS`, alias *learnAS*), controlled by decision **[AS-027]** (and original scope
> **[AS-012]**). Each topic ends with a **"What this means for patrecAS"** synthesis tied to the
> *real* AgentSuite seams (the AS-006 event log, the Phase-6 derived memory, `Registry.route()`,
> `agents install`). The companion files are `architecture.md` (the design), `decisions.md` (ADRs
> `PAT-001…`), and `plan.md` (the phased roadmap).
>
> **Citation integrity.** Every source tagged `[verified]` was opened during this deep-dive (arXiv
> abstract/API) and confirmed to say what is claimed. Sources tagged `[unverified]` are well-known
> works named from prior knowledge but **not** opened here — they are never used as the sole support
> for a novelty/feasibility verdict. Full list in the **Bibliography**.
>
> **Reading style.** Bottom line first in each section, then the evidence. Technical terms are
> glossed in plain language on first use.

---

## 0. Executive summary (the bottom line)

**The user asked for an "RLHF-type learning model." Taken literally that is infeasible here, and the
deep dive confirms the README/[AS-027] reframing is the correct one.** True RLHF (Reinforcement
Learning from Human Feedback) and its lighter cousin DPO (Direct Preference Optimization) both
*update the weights of a language model you own*. AgentSuite does **not** own the planner model: every
agent is a black-box `copilot` process (Backend A), invoked headlessly. You cannot run a policy
gradient through a vendor LLM you only call by API. So "RLHF on the Copilot weights" is a non-starter
until/unless a **self-hosted planner** is adopted (Backend C).

**The feasible and well-supported reframing:** *preference-based adaptation over the surface
AgentSuite actually controls* — the agent **prompts/descriptions**, the **routing**, the **registry
manifests**, and the **roster** itself. This is not a downgrade; it is exactly where the modern
literature has moved for black-box LLMs. Four mature research lines map cleanly onto AgentSuite's
existing seams:

| Adaptation lever (what patrecAS can change) | Research line that validates it | AgentSuite seam it writes |
|---|---|---|
| **What the manager knows about the user** (in-context personalization) | Retrieval/memory-based personalization; *Generative Agents* memory stream | Phase-6 facts + vector index (AS-023) |
| **What each agent's prompt/description says** | Prompt optimization: DSPy, OPRO, APO/ProTeGi, TextGrad, GEPA | persona `.md` + `registry/v1` `when_to_use`/`summary` |
| **Which agent gets a task** (online discrete choice) | Contextual bandits: LinUCB, Thompson sampling | `Registry.route()` scoring |
| **Which agents exist at all** (roster growth) | Automated agent design: ADAS, AutoAgents, Voyager skill library | new `<name>AS.md` + manifest via `agents install` |

**Recommended staged sequence (matches [AS-027] exactly): A → E → B → C → D.**
- **A** — retrieval-based personalization on the Phase-6 substrate (lowest risk, ships first).
- **E** — new-agent induction (detect a roster gap → propose persona + manifest → human-approve → install).
- **B** — approved, versioned, A/B-evaluated prompt/manifest diffs.
- **C** — a contextual-bandit slice over routing/templates with a learned reward model.
- **D** — DPO/weight-level RLHF: **research-only**, contingent on a self-hosted planner.

**The single biggest risk is not capability, it is Goodhart's law** (optimizing a proxy metric until
the proxy improves but real quality degrades). Every stage past A must be gated by *propose-not-apply*,
human approval, and an experimentAS A/B test before adoption — which is precisely the safety posture
[AS-027] already locks in.

---

## 1. Framing: is this really "RLHF"? (preference learning over a black-box surface)

**Bottom line: keep the *preference-learning* idea, drop the *weight-update* mechanism. Adapt the
controllable surface, not the LLM.**

### 1.1 What RLHF / DPO actually require

- **RLHF** (the InstructGPT recipe) is a three-step pipeline: supervised fine-tune → train a **reward
  model** from human preference comparisons → fine-tune the LLM with reinforcement learning (PPO) to
  maximize that reward without drifting too far from the base model [InstructGPT, Ouyang et al. 2022,
  arXiv:2203.02155, *verified*]. Every step that matters **changes model weights**.
- **DPO** removes the separate reward model and the RL loop: it shows the LLM "is secretly a reward
  model" and can be aligned to preference pairs with a simple classification loss — *stable,
  lightweight, no sampling during fine-tuning* [DPO, Rafailov et al. 2023, arXiv:2305.18290,
  *verified*]. But DPO **still fine-tunes the LLM's weights**. Variants in the same family (KTO, which
  needs only thumbs-up/down rather than pairs [KTO, Ethayarajh et al. 2024, arXiv:2402.01306,
  *verified*]; IPO [Azar et al. 2023, *unverified*]) all share that requirement.
- **RLAIF / Constitutional AI** replaces *human* preference labels with *AI-generated* ones against a
  written "constitution," cutting labeling cost — but again the payoff is a fine-tuned model
  [Constitutional AI, Bai et al. 2022, arXiv:2212.08073, *verified*].

**Implication.** All of these are off the table for the Copilot planner, which AgentSuite calls as an
opaque process (`copilot --agent … -p …`, Backend A, architecture §AgentRunner). There is no weight
access, no gradient, no place to put a reward signal *inside* the model.

### 1.2 The black-box precedent

The strongest agentic systems of the last two years deliberately **avoid** fine-tuning and instead
learn in-context. Voyager states it plainly: it "interacts with GPT-4 via blackbox queries, which
bypasses the need for model parameter fine-tuning," and still achieves lifelong skill growth via an
**ever-growing skill library** and iterative prompting [Voyager, Wang et al. 2023, arXiv:2305.16291,
*verified*]. This is the template patrecAS should follow: *learning lives in retrievable artifacts and
edited prompts/roster, not in weights.*

### 1.3 The reframing, stated precisely

patrecAS performs **preference-based adaptation of a controllable, discrete, inspectable surface**:

1. **In-context personalization** — inject a learned user/team model into the manager's planning
   context (retrieval, not training).
2. **Prompt/description optimization** — improve persona `.md` bodies and manifest `when_to_use`
   text (text-space optimization, §3).
3. **Routing as online decision-making** — treat "which agent / which template" as a bandit action
   (§4).
4. **Roster induction** — add a new agent when no existing one fits (§5).

Where DPO-style preference learning *can* eventually apply is layer (4)-of-RLHF — the **reward model**
— which is just a learned scorer over (context, action, outcome). That is reusable for the bandit in
Stage C **without any LLM fine-tuning**. Only Stage D (a self-hosted planner) reopens true DPO/RLHF.

> **What this means for patrecAS.** The README framing is **validated and sharpened**: "RLHF-type"
> = *preference signal in, behavioural adaptation out, over prompts/routing/manifests/roster.* The
> reward-modeling *concept* from RLHF survives and is reused (Stage C); the weight-update *mechanism*
> is deferred to Stage D behind a self-hosted-planner contingency. This belongs in `decisions.md` as
> **PAT-001**.

---

## 2. Reward signal design from AgentSuite's real telemetry

**Bottom line: AgentSuite already emits a rich implicit-feedback stream in the AS-006 event log; treat
it as a *noisy, biased* reward proxy, fuse it with explicit AS-025 thumbs, and never optimize it
without a guardrail metric.**

### 2.1 What the event log already gives us (implicit feedback)

The append-only `events` table (`store.py`) records typed events the orchestrator emits:
`plan_validated`, `node_started`, `node_completed`, `node_failed`, `approval_requested`,
`approval_granted`, `run_completed`. From these, patrecAS can derive — **read-only**, by folding the
log — signals that are classic implicit-feedback proxies:

| Raw event evidence | Derived signal | Interpretation (reward sign) |
|---|---|---|
| `approval_granted` vs `approval_denied`/`approval_required` failure | **plan acceptance rate** | strong + / − on a plan or an agent choice |
| `ts(approval_granted) − ts(approval_requested)` | **time-to-accept** | low = confident accept (+); high = friction |
| `--from`/`--to` partial re-runs, repeated `node_started` for same node | **re-run / redo count** | − on the re-run agent or its output |
| `node_failed` payload `{error}` per agent | **failure rate by agent/capability** | − on reliability |
| run ends without `run_completed` (abandonment) | **abandonment** | − on the whole plan |
| downstream artifact edits before acceptance | **edit distance to accepted artifact** | − proportional to edits |
| `cost.total_tokens` / durations (AS-018) | **cost** | guardrail (not reward) |

### 2.2 Explicit feedback (AS-025 conversational UI)

The future conversational surface (AS-025) is the channel for **explicit** thumbs/ratings/edits.
KTO is directly relevant: it shows you can align from *binary* desirable/undesirable judgements
without paired comparisons [KTO, arXiv:2402.01306, *verified*] — a good fit for a thumbs-up/down UI
and for training a reward scorer (Stage C) even if no LLM fine-tuning happens.

### 2.3 The hazards (why implicit feedback is not ground truth)

- **Selection/position bias and noise.** Implicit signals confound quality with convenience (the user
  may accept a mediocre plan because re-planning is costly). The bandit/IR literature treats clicks as
  *biased* feedback requiring debiasing; patrecAS must too.
- **Reward misspecification → specification gaming.** Optimizing a proxy can *map* to a misaligned
  policy: more capable optimizers exploit proxy gaps harder, and the true-vs-proxy reward can
  diverge sharply (a phase-transition-like effect) [The Effects of Reward Misspecification, Pan et al.
  2022, arXiv:2201.03544, *verified*]. This is the formal statement of the Goodhart risk.

> **What this means for patrecAS.** Define a **typed `feedback/v1` read-model** computed *by folding
> the event log* (never by mutating it — append-only is enforced by DB triggers). Fuse implicit
> signals with explicit AS-025 ratings into a per-(user, agent, capability, template) reward estimate
> with **uncertainty** attached (needed by the bandit in Stage C). Always carry a separate
> **guardrail metric** (e.g., human accept on a held-out sample) that the optimizer is *not* allowed
> to touch. ADR **PAT-005**.

---

## 3. Self-improving / self-modifying agents & prompt optimization

**Bottom line: text-space optimization of prompts/descriptions is real, cheap, and effective — and
it is the natural fit for AgentSuite's `.md` personas and `when_to_use` manifest text. But every
known method is fragile under reward hacking, drift, and prompt injection, so patrecAS must *propose*
edits and gate them behind A/B + human approval.**

### 3.1 What works (the toolbox)

- **DSPy** — treat an LLM pipeline as a program of declarative modules and *compile/optimize* it
  against a metric by bootstrapping demonstrations; reports 25–65% gains over hand-written few-shot
  prompts [DSPy, Khattab et al. 2023, arXiv:2310.03714, *verified*]. The mental model patrecAS should
  adopt: *prompts are parameters, the metric is the objective.*
- **OPRO** — "LLM as optimizer": describe the optimization in natural language, feed back prior
  candidate prompts + scores, let the LLM propose better ones; up to +8% GSM8K, +50% on Big-Bench
  Hard over human prompts [OPRO, Yang et al. 2023, arXiv:2309.03409, *verified*].
- **APO / ProTeGi** — "gradient descent in text": minibatches of data produce natural-language
  "gradients" (critiques) that edit the prompt in the opposite semantic direction, steered by beam
  search + **bandit selection**; up to +31% [Automatic Prompt Optimization, Pryzant et al. 2023,
  arXiv:2305.03495, *verified*]. Note the bandit appears *inside* prompt optimization — a direct hint
  for Stage C.
- **TextGrad** — backpropagate *textual* feedback through a compound multi-LLM system, PyTorch-style,
  to optimize any component (prompts, code, even molecules) [TextGrad, Yuksekgonul et al. 2024,
  arXiv:2406.07496, *verified*].
- **GEPA** — reflective *prompt evolution*: sample trajectories, reflect in natural language to
  diagnose failures, mutate prompts, and keep a Pareto frontier of attempts; **outperforms GRPO
  (an RL method) by up to 20% using up to 35× fewer rollouts** [GEPA, Agrawal et al. 2025,
  arXiv:2507.19457, *verified*]. This is the headline empirical case that *language-space learning can
  beat policy-gradient RL* for adapting black-box LLMs — strong external support for the patrecAS
  reframing.
- **Reflexion / Self-Refine** — agents improve via *verbal* self-feedback stored in an episodic memory
  and re-injected, no weight updates [Reflexion, Shinn et al. 2023, arXiv:2303.11366, *verified*;
  Self-Refine, Madaan et al. 2023, arXiv:2303.17651, *verified*, ~20% absolute average gain].

### 3.2 What is fragile (the failure modes patrecAS must design against)

- **Reward hacking / Goodhart.** Text optimizers happily overfit the eval metric; combined with
  reward-misspecification effects [Pan et al. 2022, *verified*] this is the dominant risk. Mitigation:
  small held-out guardrail set, multiple metrics, human accept as the final gate.
- **Drift / catastrophic forgetting.** Iterated self-edits can wander; Voyager explicitly designs the
  skill library to *alleviate* catastrophic forgetting [Voyager, *verified*]. Mitigation: every edit
  is a *versioned git diff* (reversible), never an in-place mutation.
- **Prompt injection via learned data.** If patrecAS learns from artifacts/feedback that an upstream
  agent or a malicious user produced, that text can carry instructions that hijack a later prompt —
  indirect prompt injection is a demonstrated real-world attack [Greshake et al. 2023,
  arXiv:2302.12173, *verified*]. AgentSuite already treats artifacts as **untrusted data** mediated by
  the orchestrator [AS-003]; patrecAS must inherit that — learned signals are data, never instructions.
- **Self-modification instability.** Fully self-rewriting agents (Gödel-machine lineage) are powerful
  in principle but unstable in practice; the recent **Darwin Gödel Machine** evolves self-improving
  agents through an archive + empirical validation rather than provable rewrites [DGM, Zhang et al.
  2025, arXiv:2505.22954, *verified*]. The lesson for patrecAS: **archive + empirical A/B validation +
  human gate**, not unconstrained self-rewrite.

> **What this means for patrecAS.** Adopt the *prompts-are-parameters* framing (DSPy/OPRO/GEPA) for
> Stage B, but constrained to AgentSuite's posture: (1) the **proposer** generates a candidate diff to
> a persona `.md` or a manifest `when_to_use`/`summary`; (2) the diff is **never auto-applied**; (3)
> experimentAS A/Bs it; (4) a human approves; (5) it lands as a **git-versioned, reversible** change
> via `agents install`. GEPA/Self-Refine's reflective loop is the *generator*; the A/B + approval gate
> is the *filter*. ADR **PAT-003**.

---

## 4. Contextual bandits for online routing/template choice

**Bottom line: the routing decision ("which agent / which prompt template for this need") is a
textbook contextual-bandit problem, and LinUCB/Thompson sampling give principled online learning with
uncertainty — but only adopt it after Stages A/E/B, and evaluate it *offline first* via replay.**

### 4.1 Why a bandit, not full RL

A **contextual bandit** chooses one action (agent/template) given a context (the task/user features),
observes a single reward (was the plan accepted? re-run?), and balances **exploration vs
exploitation**. It is the right tool when actions are *discrete*, feedback is *immediate-ish*, and
there is no long horizon of state transitions to credit — exactly AgentSuite routing. The canonical
result is **LinUCB**: a contextual-bandit approach to personalized recommendation that beat
context-free methods and, crucially, introduced an **unbiased offline evaluation** method using logged
data [Li et al. 2010, arXiv:1003.0146, *verified*]. **Thompson sampling** is the Bayesian alternative
(sample a model from the posterior, act greedily w.r.t. it) — simple and strong in practice
[Thompson-sampling tutorial, Russo et al. 2018, *unverified*].

### 4.2 The offline-evaluation unlock

The same Li et al. work shows you can **evaluate a new routing policy on *logged* data** (replay /
inverse-propensity weighting) without deploying it live [arXiv:1003.0146, *verified*]. This is gold
for AgentSuite: the **event log is exactly such a log**, and runs are already **replayable** (the log
is the source of truth; `reconstruct`/`--resume` exist). patrecAS can therefore *counterfactually*
estimate "would this routing tweak have been accepted more often?" before risking a live change.

### 4.3 Where it plugs in

`Registry.route(need)` today is a deterministic lexical scorer (capability/phrase/token overlap). A
bandit does **not** replace it; it **re-ranks** its candidates using a learned reward estimate +
exploration bonus, keyed on (user/team features, capability tokens, agent). The deterministic scorer
remains the safe default and the cold-start prior.

> **What this means for patrecAS.** Stage C adds a **bandit re-ranker** over `route()` output, with the
> reward model from §2 and **per-arm uncertainty**. Mandatory sequencing: build the **offline replay
> estimator first** (§4.2) and require it to predict a win *before* any online exploration is enabled;
> cap exploration and keep the lexical scorer as fallback. ADR **PAT-004**. This is explicitly *after*
> the cheaper Stages A/E/B because it is the highest-machinery, highest-Goodhart-risk lever.

---

## 5. New-agent induction (roster growth when there is a capability gap)

**Bottom line: AgentSuite's "a new manifest is routable with no code change" design ([AS-004]) makes
roster growth unusually tractable; the research (ADAS, AutoAgents, Voyager) shows automatic
agent/role generation works, but safety demands human approval + the existing `agents install`
path.**

### 5.1 The research basis

- **ADAS (Automated Design of Agentic Systems)** — a *meta-agent* programs ever-better agents in code,
  growing an **archive** of discovered designs; invented agents outperform hand-designed ones and even
  transfer across domains/models [ADAS, Hu et al. 2024, arXiv:2408.08435, *verified*]. The paper
  explicitly flags "*provided we develop it safely*" — matching AgentSuite's human-gated posture.
- **AutoAgents** — *adaptively generates and coordinates* specialized agents (a "role" per task) with
  an **observer** role that reflects on the generated plan/agents and improves them [AutoAgents, Chen
  et al. 2023, arXiv:2309.17288, *verified*]. This is the closest analogue to "induct a new `<name>AS`."
- **Voyager skill library** — new *skills* (here: new capabilities) are induced from need and stored
  for reuse [Voyager, *verified*]. patrecAS treats a new agent as a coarse-grained, human-approved
  "skill."

### 5.2 The induction pipeline grounded in real seams

1. **Gap detection.** Monitor `Registry.route(need)` top scores over the event log. A *repeated* need
   whose best agent score sits below a threshold (or repeated escalations / `node_failed` with
   "no suitable agent") is a candidate gap. (The `route()` scorer already returns numeric scores +
   reasons, so this is a read-only fold.)
2. **Cluster the unmet needs.** Embed the unmet `need` strings with the Phase-6 `Embedder` seam
   (zero-dep `HashingEmbedder` default) and cluster by cosine threshold (zero-dep agglomerative) to
   find a *recurring* missing capability — not a one-off.
3. **Draft the agent.** A meta-step (LLM, ADAS/AutoAgents pattern) drafts a candidate **`<name>AS.md`
   persona** (honoring the LOCKED naming convention) **+ a `registry/v1` manifest** (`capabilities`,
   `consumes`, `produces`, `when_to_use`, `approval_default`). The manifest is schema-validated by the
   existing `AgentManifest.from_dict` validator.
4. **Human approval gate.** Surfaced via AS-025 / the orchestrator approval gate — *propose-not-apply*.
5. **Install reversibly.** On approval, write the files into repo `agents/` + `registry/`, commit
   (git-versioned, reversible), and run `agentsuite agents install`. Because routing is registry-driven
   [AS-004], the new agent is immediately routable **with no code change**.

### 5.3 The hazards

Auto-generated agents can be redundant (overlap an existing agent), low-quality, or — if drafted from
injected/learned text — adversarial. Mitigations: dedupe against existing manifests (capability cosine
similarity), require an experimentAS evaluation that the new agent actually *wins* the clustered need,
and never bypass the human gate.

> **What this means for patrecAS.** This is **Stage E**, scheduled *second* (right after retrieval
> personalization) precisely because the registry design makes it low-friction and high-value, and
> because it composes with everything else. ADR **PAT-006**. It reuses: `route()` scores (gap signal),
> the `Embedder` (clustering), the manifest validator (well-formedness), the orchestrator approval
> gate (human sign-off), and `agents install` (deployment).

---

## 6. Memory / retrieval-based personalization (Stage A, the MVP)

**Bottom line: the cheapest, safest, first thing to build is a *retrieved user/team model* — and
AgentSuite already has the entire substrate for it from Phase 6.**

The *Generative Agents* line shows a **memory stream** (observations stored, then **retrieved by
relevance/recency/importance** and synthesized into higher-level reflections) produces believable,
personalized long-horizon behaviour with **no fine-tuning** [Generative Agents, Park et al. 2023,
arXiv:2304.03442, *verified*]. That architecture is essentially what AgentSuite's Phase-6 derived
memory already is: append-only events → **agent-namespaced facts** (with `source` provenance +
`supersedes`) → a **knowledge graph** + a **vector index** with semantic `search()` [AS-023,
`derived.py`].

> **What this means for patrecAS.** Stage A writes a **user/team model as `facts` namespaced to
> `agent="patrecAS"`** (preferences, expertise level, style, recurring goals, per-agent performance
> stats), each with `source` provenance, updated via `supersedes` (never mutated — the R5 pattern).
> managerAS *reads* it at plan time via `DerivedMemory.search()` / `facts_for(agent="patrecAS")`. No
> new storage tech, no new dependency, fully local-first, deterministic. This realizes the [AS-012]
> seam (patrecAS = writer, managerAS = reader) and is the safe foundation everything else builds on.

---

## 7. Privacy, safety & governance

**Bottom line: behavioural learning is privacy- and safety-sensitive; AgentSuite's existing posture
(local-first, append-only audit, untrusted-data containment, approval gates) already supplies most of
the controls, and patrecAS must inherit all of them plus add reset/opt-out.**

| Control | Mechanism in AgentSuite | patrecAS obligation |
|---|---|---|
| **Local-first, no 3P sharing** | single local SQLite, no egress [AS-007] | behavioural data never leaves the machine; HashingEmbedder default avoids API-embedding egress |
| **Propose-not-apply** | orchestrator approval gate [AS-005] | every prompt/manifest/roster diff is a *proposal* |
| **Versioned & reversible** | repo `agents/`+`registry/` under git; `agents install` idempotent, never clobbers without `--force` [AS-024] | all edits land as reviewable git diffs; one-command rollback |
| **Audit / replay** | append-only event log, `reconstruct` [AS-006] | every adaptation decision logged as an event; fully reconstructable |
| **Injection containment** | artifacts are untrusted data; orchestrator mediates I/O [AS-003] | learned signals are *data*, never instructions (defends [Greshake 2023, *verified*]) |
| **Anti-Goodhart** | experimentAS A/B (Phase 7 self-experimenting suite) | no adaptation adopted without an A/B win on a guardrail metric [Pan et al. 2022, *verified*] |
| **Reset / opt-out** | *(new)* | a `patrecAS reset`/opt-out that drops the user model + reverts learned diffs; learning is off by default until opted-in |

> **What this means for patrecAS.** Governance is not a bolt-on; it is the *enabling* design. The
> module is **safe by construction** because it can only ever emit proposals into the existing
> human-gated, git-versioned, append-only, local-first machinery. ADR **PAT-007**.

---

## 8. Cross-cutting synthesis & novelty note

- **Novelty verdict (engineering, not science): Substantially Integrative.** None of the *individual*
  techniques are novel — preference learning, prompt optimization, contextual bandits, agent
  induction, and retrieval personalization are all established (citations above). The **defensible
  contribution** is the *integration*: a **local-first, zero-dependency, fully-auditable, human-gated
  adaptive layer** that learns over an **append-only event-sourced substrate** and adapts a
  **registry-routed multi-agent roster** — including **inducting new agents** — without ever touching
  LLM weights. The combination of (event-sourced reward signal) × (propose-not-apply git-versioned
  agent edits) × (offline-replay-evaluated bandit routing) × (registry-driven zero-code agent
  induction) is, to this survey's knowledge, not a packaged prior system. *Confidence: medium* — the
  component literature is well covered; a dedicated prior-art/patent sweep (a `priorart.*.md`) is the
  recommended next research step before any publication/patent claim.
- **Where the user's intuition needed reshaping:** "RLHF" → preference-based adaptation of the
  controllable surface; "a learning model" → a *retrieved, versioned user/team model + a reward
  estimator*, not a fine-tuned network. GEPA's result (language-space learning beating RL with 35×
  fewer rollouts [arXiv:2507.19457, *verified*]) is the clearest evidence the reframing is not a
  compromise but, for black-box LLMs, often the *better* engineering choice.

---

## Bibliography

Verification tags reflect what was opened during this deep-dive (arXiv `abs` page and/or the arXiv
API `summary`). `[verified]` = opened and confirmed; `[unverified]` = named from prior knowledge,
not opened here, and not used as sole support for any verdict.

**Preference learning / alignment**
- Ouyang et al. (2022), *Training language models to follow instructions with human feedback*
  (InstructGPT/RLHF). arXiv:2203.02155. `[verified]`
- Rafailov et al. (2023), *Direct Preference Optimization: Your Language Model is Secretly a Reward
  Model*. arXiv:2305.18290. `[verified]`
- Ethayarajh et al. (2024), *KTO: Model Alignment as Prospect Theoretic Optimization*.
  arXiv:2402.01306. `[verified]`
- Bai et al. (2022), *Constitutional AI: Harmlessness from AI Feedback* (RLAIF). arXiv:2212.08073.
  `[verified]`
- Azar et al. (2023), *A General Theoretical Paradigm to Understand Learning from Human Preferences*
  (IPO). `[unverified]`

**Prompt / system optimization (text-space)**
- Khattab et al. (2023), *DSPy: Compiling Declarative Language Model Calls into Self-Improving
  Pipelines*. arXiv:2310.03714. `[verified]`
- Yang et al. (2023), *Large Language Models as Optimizers* (OPRO). arXiv:2309.03409. `[verified]`
- Pryzant et al. (2023), *Automatic Prompt Optimization with "Gradient Descent" and Beam Search*
  (APO/ProTeGi). arXiv:2305.03495. `[verified]`
- Yuksekgonul et al. (2024), *TextGrad: Automatic "Differentiation" via Text*. arXiv:2406.07496.
  `[verified]`
- Agrawal et al. (2025), *GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning*.
  arXiv:2507.19457. `[verified]`
- Zhou et al. (2022), *Large Language Models Are Human-Level Prompt Engineers* (APE).
  arXiv:2211.01910. `[verified]` (title/ID confirmed)

**Self-improving / self-modifying agents**
- Shinn et al. (2023), *Reflexion: Language Agents with Verbal Reinforcement Learning*.
  arXiv:2303.11366. `[verified]` (title/ID confirmed)
- Madaan et al. (2023), *Self-Refine: Iterative Refinement with Self-Feedback*. arXiv:2303.17651.
  `[verified]`
- Wang et al. (2023), *Voyager: An Open-Ended Embodied Agent with Large Language Models*.
  arXiv:2305.16291. `[verified]`
- Zhang et al. (2025), *Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents*.
  arXiv:2505.22954. `[verified]` (title/ID confirmed)

**Automated agent / multi-agent design**
- Hu, Lu, Clune (2024), *Automated Design of Agentic Systems* (ADAS / Meta Agent Search).
  arXiv:2408.08435. `[verified]`
- Chen et al. (2023), *AutoAgents: A Framework for Automatic Agent Generation*. arXiv:2309.17288.
  `[verified]`

**Contextual bandits / online learning / offline evaluation**
- Li et al. (2010), *A Contextual-Bandit Approach to Personalized News Article Recommendation*
  (LinUCB + offline policy evaluation). arXiv:1003.0146. `[verified]`
- Russo et al. (2018), *A Tutorial on Thompson Sampling*. arXiv:1707.02038. `[unverified]`

**Memory / retrieval personalization**
- Park et al. (2023), *Generative Agents: Interactive Simulacra of Human Behavior*. arXiv:2304.03442.
  `[verified]` (title/ID confirmed)

**Safety / failure modes**
- Pan et al. (2022), *The Effects of Reward Misspecification: Mapping and Mitigating Misaligned
  Models*. arXiv:2201.03544. `[verified]` (title/ID confirmed)
- Greshake et al. (2023), *Not what you've signed up for: Compromising Real-World LLM-Integrated
  Applications with Indirect Prompt Injection*. arXiv:2302.12173. `[verified]`
- OWASP (2023–), *Top 10 for LLM Applications* (LLM01 Prompt Injection). `[unverified]`
