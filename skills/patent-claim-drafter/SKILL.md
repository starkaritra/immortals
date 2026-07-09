---
name: patent-claim-drafter
description: >
  patentAS-family skill for drafting and stress-testing patent claim sets. Triggers on:
  "draft claims for this invention", "write patent claims", "review my independent claims",
  "where can a competitor design around this", "build a claim tree", "dependent claims for".
  Owns the durable craft of writing a clean independent claim, laddering dependent claims,
  checking antecedent-basis and single-sentence form, and probing design-around gaps and
  §101/§112 risks. Use when an invention needs a claim set or an existing set needs review.
  Do NOT use it to file — drafting and strategy only; a registered attorney reviews filings.
argument-hint: "Describe the invention: the problem, the core inventive step, and key components"
owner-agent: patentAS
version: 1.0.0
---

# patent-claim-drafter Skill

Draft claim sets that are broad enough to be worth having and tight enough to survive — and
find where a competitor could design around them.

> Not legal advice. This produces attorney-reviewable drafts, not filings.

## When to use
- An invention needs a first claim set (independent + dependent ladder).
- An existing claim set needs a scope/quality review.

## Anatomy of a good claim set
1. **Independent claim(s) — as broad as the prior art allows.**
   - Single sentence, structured: preamble → transitional phrase (`comprising` = open) →
     body of elements. One inventive concept per independent claim.
   - Include *only* the elements essential to novelty. Every extra limitation narrows scope
     and hands competitors a design-around.
   - Provide independent claims in multiple statutory categories where apt (method / system /
     computer-readable medium) to cover different infringers.
2. **Dependent claim ladder — fallback positions.**
   - Each adds one limitation (an optional feature, a narrower range, a specific embodiment).
   - Ladder from broad → narrow so that if a broad claim falls to prior art, a narrower one
     survives. Group by feature family.

## Drafting checklist (§112 hygiene)
- **Antecedent basis:** every "the/said X" has a prior "a/an X". No orphan references.
- **Single sentence, definite:** no ambiguous "such as", no relative terms without a
  reference ("substantially", "about" — use with care and support in the spec).
- **Support:** every claimed element is described in the specification (enablement +
  written description). Flag claim terms not backed by the spec.
- **Consistent terminology:** the same component is named the same way throughout.

## Stress tests
- **Design-around probe:** for each independent claim, ask "what's the cheapest way to build
  the same benefit while omitting one claimed element?" If easy, the claim is too narrow —
  propose a broader independent claim or a blocking dependent claim.
- **§101 eligibility (esp. software/AI):** does the claim recite a concrete technical
  improvement, or a bare abstract idea "apply it on a computer"? Reframe around the specific
  technical mechanism and its effect. (See the **prior-art-search** skill for §102/§103.)

## Output
```
CLAIM SET — <invention>
Independent 1 (method):   <claim text>
Independent N (system/CRM): …
Dependent ladder:
  2. (depends 1) <+ limitation>   — purpose: <fallback rationale>
  …
Scope notes:      <what's covered / not covered>
Design-around gaps: <where a competitor slips through> + proposed blocking claims
§101/§112 flags:  <risks + fixes>
```

## Handoff
Pairs with **prior-art-search** (novelty/obviousness grounding) and the **novelty-log**
(claim differentiation). patentAS owns filing strategy; a registered practitioner reviews.
