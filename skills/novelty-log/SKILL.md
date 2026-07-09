---
name: novelty-log
description: >
  researchAS/paperAS/patentAS-family skill for maintaining a running novelty log — a durable
  record of what is new in a project versus the relevant prior art, updated as decisions are
  made. Triggers on: "track our novelty", "update the novelty log", "what's new vs prior
  art", "which decisions strengthen our claim", "novelty.md", "IP hygiene". Owns the durable
  craft of stating each novel element, the closest prior art, the delta, and how each design
  decision strengthens or weakens the claim. Use for projects with publication or patent
  goals. Skip for projects with no such goals.
argument-hint: "Tell me the project's core claimed contribution(s), or point me at novelty.md"
owner-agent: researchAS
requires: [literature-search]
version: 1.0.0
---

# novelty-log Skill

Keep an honest, sourced ledger of what's genuinely new — so publication/patent claims are
defensible and design decisions are evaluated for their effect on novelty.

## When to use
- The project has a paper or patent goal (IP hygiene per coderAS rule 9).
- A design decision might strengthen or weaken a novelty claim.
- Positioning work against prior art.

## What the log contains (`novelty.md`)
Append-only, one block per claimed novel element:

```
## [NOV-NNN] <short name of the novel element>
- Date: YYYY-MM-DD
- Status: candidate | supported | weakened | abandoned
- Claim: <what is new, in one precise sentence>
- Closest prior art: <work(s)> — <what they do>  [source: DOI/arXiv/link]
- Delta: <the specific difference that makes this novel>
- Evidence: <experiment/result/design fact that supports the delta>  [source]
- Risk to claim: <what could invalidate it — an existing paper, an obvious extension>
- Linked decisions: <decisions.md anchors that strengthen/weaken this>
```

## Method
1. **Elicit the claimed contributions** (from the owner, README, or paperAS/patentAS).
2. **Anchor each against prior art** — run or request the **literature-search** skill; record
   the closest work and the concrete delta. Never assert novelty without a search behind it.
3. **Track decision impact.** When a decision is recorded in `decisions.md`, note whether it
   strengthens, weakens, or is neutral to each novelty element, and update status.
4. **Surface risks early.** Flag any element whose delta is thin ("obvious extension") so the
   owner can strengthen or drop it before investing.

## Output
- The maintained `novelty.md` (create if absent).
- A short delta report on each update: what changed, and the current novelty posture
  (which claims are strong, which are at risk).

## Guardrails
- Every novelty assertion carries provenance (the prior-art search + date).
- Be adversarial toward your own claims — assume a reviewer/examiner will find the nearest
  prior art; write the log to survive that.
- Distinguish **novel** (nobody did it) from **non-obvious** (patent bar) from **significant**
  (worth publishing) — a claim can be one without the others.

## Handoff
Feeds **paperAS** (contributions/positioning) and **patentAS** (claim differentiation);
pulls from the **literature-search** skill for prior-art grounding.
