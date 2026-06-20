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
Scaffold only. **researchAS is running a deep dive** and will author/maintain the docs in `design/`
(architecture, the literature/landscape deep-dive, decisions, and a phased plan). No code yet.

## Layout
```
patrecAS/
  README.md         <- this file
  design/           <- module-specific design docs (authored by researchAS)
```
