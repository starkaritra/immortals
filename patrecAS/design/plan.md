# patrecAS / learnAS — Plan

> Phased, buildable roadmap for the adaptive-learning module. Order is locked by **[PAT-002]** to the
> [AS-027] sequence **A → E → B → C → D**, i.e. increasing risk and machinery. Each phase has an
> explicit **exit** (definition of done) consistent with the Immortals coderAS bar: code runs · tests
> pass · result measured & logged · docs + provenance updated. Research grounding: `deep-dive.md`;
> architecture: `architecture.md`; decisions: `decisions.md`.
>
> **Status:** not started — design only. No code yet.

---

## Phase 0 — Scaffold & contracts (foundation)
- [ ] Add the four additive schemas + validators: `feedback/v1`, `user_model/v1`,
  `adaptation_proposal/v1`, `agent_induction/v1` (reuse the existing `validate()` convention).
- [ ] Author `patrecAS.md` persona + `registry/v1` manifest (PAT-010); register so `route()` can reach
  it. LOCKED `<name>AS.md` naming.
- [ ] Module skeleton `patrecAS/` (Python) with read-only access to `MemoryStore` / `DerivedMemory`
  via `config.py` paths (no new deps).
- **Exit:** schemas validate round-trip; `patrecAS` is routable (`immortals route "learn my
  preferences"` ranks it); zero new third-party dependencies; deterministic tests green.

## Phase A — Retrieval-based personalization (MVP, lowest risk) — *ships first*
- [ ] **SignalExtractor**: fold the event log into a `feedback/v1` read-model (plan acceptance,
  time-to-accept, re-runs, per-agent failure, abandonment, cost). Pure function of the log; rebuildable.
- [ ] **UserTeamModel writer**: derive a `user_model/v1` (preferences, expertise, style, goals,
  per-agent stats) and persist it as `facts(agent="patrecAS")` with `source` + `supersedes` (additive,
  never mutated — R5 pattern).
- [ ] **Serve to managerAS**: structured (`facts_for(agent="patrecAS")`) + semantic
  (`DerivedMemory.search(..., agent="patrecAS")`) reads; a `patrecAS model` CLI/MCP read.
- [ ] managerAS reads the model at plan time (the [AS-012] seam — reader side).
- **Exit:** over a real multi-run history, managerAS retrieves a correct, provenance-tagged user model
  and demonstrably changes a plan because of it; **pure read — no adaptations applied**; tests pass.
- **Risk:** lowest (no writes to the controllable surface). **Goodhart exposure:** none.

## Phase E — New-agent induction (high value, low friction) — *second*
- [ ] **GapDetector**: fold the log for needs whose best `Registry.route()` score is sub-threshold /
  repeated escalations.
- [ ] **NeedClusterer**: embed unmet `need` strings via the Phase-6 `Embedder`; cosine-cluster
  (zero-dep) to confirm a *recurring* gap.
- [ ] **AgentInductor**: draft `<name>AS.md` persona + schema-validated `registry/v1` manifest;
  dedupe against existing manifests by capability similarity → emit `agent_induction/v1` (proposal).
- [ ] **Governance path**: human approval (orchestrator gate / AS-025) → git commit → `agents install`;
  reversibility verified. (Optionally: an experimentAS check that the new agent wins the clustered need.)
- **Exit:** from a synthetic gap, patrecAS proposes a well-formed `<name>AS` + manifest, a human
  approves, `agents install` makes it **routable with no code change** ([AS-004]), and a `git revert`
  cleanly removes it. **Never auto-installs.**
- **Risk:** medium (adds a roster member) but fully human-gated + reversible.

## Phase B — Approved, versioned, A/B-evaluated prompt/manifest diffs
- [ ] **AdaptationProposer**: generate `adaptation_proposal/v1` diffs to persona `.md` bodies and
  manifest `when_to_use`/`summary` (reflective prompt-optimization pattern — DSPy/OPRO/GEPA; *output is
  a proposal*, not an applied edit).
- [ ] **A/B gate**: experimentAS evaluates each proposal over replayable tasks; require a win on the
  reward proxy **and** no regression on the un-optimized guardrail metric.
- [ ] **Apply path**: human approval → git commit → `agents install`; one-revert rollback.
- **Exit:** a proposed manifest/persona edit beats control in an experimentAS A/B, is human-approved,
  lands as a git diff, and is reverted cleanly; the whole decision is in the event log.
- **Risk:** medium (edits the surface) — contained by PAT-003 gate. **Goodhart exposure:** present →
  guardrail metric mandatory.

## Phase C — Contextual-bandit routing (highest machinery, last before D)
- [ ] **RewardEstimator**: per-(user, agent, capability, template) reward + uncertainty, fusing
  implicit + explicit feedback.
- [ ] **Offline evaluator first**: inverse-propensity / replay estimator over the logged event stream
  ([arXiv:1003.0146]); require a predicted win before any online step.
- [ ] **Bandit re-ranker**: LinUCB/Thompson re-rank of `Registry.route()` candidates; deterministic
  lexical scorer stays as prior + fallback; capped, gated online exploration.
- **Exit:** the bandit beats the static `route()` on logged data offline; a capped online slice shows a
  measured, guardrail-safe improvement; exploration is bounded and reversible.
- **Risk:** highest near-term (online learning, Goodhart) — deliberately last, behind offline eval +
  PAT-003 gate.

## Phase D — DPO/weight-level RLHF (research-only, contingent)
- [ ] **Blocked** on a self-hosted/ownable planner (Backend C). Not built while the planner is a
  black-box vendor LLM (PAT-001, PAT-009).
- [ ] If/when unblocked: reuse the PAT-004 reward model as the preference signal; prefer DPO over PPO
  (simpler/stabler [arXiv:2305.18290]).
- **Exit:** n/a until the self-hosted-planner contingency is met; tracked as research.

---

## Milestone map
| Milestone | Phases | Demonstrable outcome |
|---|---|---|
| L1 — "It knows me" | 0 + A | managerAS plans differently using a retrieved, provenance-tagged user model |
| L2 — "It grows the team" | E | a human-approved, reversible new `<name>AS` becomes routable with no code change |
| L3 — "It tunes the team" | B | an A/B-won, human-approved persona/manifest diff is adopted and reversible |
| L4 — "It learns to route" | C | a bandit re-ranker beats static routing offline, then safely online |
| L5 — "It could train a planner" | D | research path, contingent on a self-hosted planner |

---

## Risk & assumption register
| # | Risk / assumption | Status | Mitigation |
|---|---|---|---|
| P1 | Implicit feedback (accept/re-run/abandon) is a noisy, biased reward proxy | Open | carry uncertainty (PAT-005); pair with an un-optimized guardrail metric; fuse explicit AS-025 signals |
| P2 | Goodhart / reward hacking when optimizing prompts/routing | Open | propose-not-apply + experimentAS A/B + guardrail metric (PAT-003); [arXiv:2201.03544] |
| P3 | Drift / forgetting from iterated self-edits | Mitigated by design | every edit is a reversible git diff; archive + empirical validation, not in-place mutation ([arXiv:2505.22954]) |
| P4 | Prompt injection via learned data | Open | learned signals are untrusted *data*, never instructions ([AS-003]; [arXiv:2302.12173]) |
| P5 | Inducted agents are redundant/low-quality/adversarial | Open | dedupe vs existing manifests; experimentAS win-check; human gate; schema validation (PAT-006) |
| P6 | No weight access to the planner (the "RLHF" ask) | Accepted constraint | reframe to controllable-surface adaptation (PAT-001); DPO/RLHF deferred to a self-hosted planner (PAT-009) |
| P7 | Online bandit exploration risks live regressions | Open | offline replay estimator first; capped exploration; static `route()` fallback (PAT-004) |
| P8 | Privacy of behavioural data | Mitigated | local-first, off-by-default, reset/opt-out, full audit (PAT-007) |

## Definition of Done (per task, coderAS bar)
Code runs · tests pass · result measured & logged (event log) · `architecture.md` + `decisions.md` +
this `plan.md` updated · provenance recorded · no new third-party dependency unless an ADR approves it.
