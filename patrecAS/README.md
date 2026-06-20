# patrecAS / learnAS — adaptive-learning module (research in progress)

> Root-level AgentSuite module. **Controlling decision:** `../design/handoff.md` → **[AS-027]**
> (and the original scope **[AS-012]**). This module keeps its **own design docs** in `design/`,
> maintained separately from the top-level AgentSuite design set.

## Purpose (one line)
Learn the user's characteristics and patterns, understand what they need, adapt each agent's
behaviour accordingly, and — when the roster has a capability gap — propose, document, and induct a
new `<name>AS.md` agent into the suite.

## Framing (to be validated by the deep dive)
"RLHF-type" here means **preference-based adaptation over the surface AgentSuite controls** — agent
prompts/descriptions, routing, registry manifests, and the agent roster — **not** gradient RLHF on
the copilot LLM weights (those aren't ownable). The reward signal is sourced from explicit/implicit
user feedback in the AS-006 event log and the (future) conversational UI (AS-025).

**Non-negotiable safety rails:** propose-not-apply; every agent-file/manifest change is
git-versioned, human-approved, and reversible; adaptations are A/B-evaluated via experimentAS before
adoption (anti-Goodhart); behavioural data stays local-first with reset/opt-out.

## Status
**Design complete (researchAS deep dive done); no code yet.** The grounded research and the module
design now live in `design/`:

- [`design/deep-dive.md`](design/deep-dive.md) — literature/landscape survey (RLHF/DPO/RLAIF,
  prompt optimization, self-improving agents, contextual bandits, agent induction, retrieval
  personalization, safety failure modes) with verified citations + a "what this means for patrecAS"
  synthesis per topic.
- [`design/architecture.md`](design/architecture.md) — module architecture over the *real* AgentSuite
  seams (AS-006 event log, Phase-6 derived memory, `Registry.route()`, `agents install`): components,
  data flow, contracts, and how managerAS consumes the user/team model.
- [`design/decisions.md`](design/decisions.md) — module ADRs `PAT-001…PAT-010` (the RLHF reframing,
  the A→E→B→C→D staging, the safety rails, new-agent induction, storage choice).
- [`design/plan.md`](design/plan.md) — the phased, buildable roadmap.

**Headline finding:** literal RLHF is infeasible (no weights to train on the black-box Copilot
planner); the validated reframing is **preference-based adaptation over the controllable surface**
(prompts, routing, manifests, roster). Staged **A → E → B → C → D**; DPO/weight-level RLHF is
research-only, contingent on a self-hosted planner.

## Layout
```
patrecAS/
  README.md         <- this file
  design/
    deep-dive.md    <- literature/landscape survey (centerpiece)
    architecture.md <- module architecture over AgentSuite's real seams
    decisions.md    <- module ADRs (PAT-001…)
    plan.md         <- phased roadmap (A→E→B→C→D)
```
