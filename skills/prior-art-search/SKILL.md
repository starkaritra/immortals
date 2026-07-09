---
name: prior-art-search
description: >
  patentAS-family skill for prior-art and freedom-to-operate searches. Triggers on: "do a
  prior-art search", "is this patentable", "search patents for", "freedom to operate", "FTO
  check", "has this been patented", "novelty/obviousness search", "§102/§103". Owns the
  durable craft of building a search around an invention's inventive step, querying patent
  and non-patent literature (Google Patents, USPTO/EPO/WIPO, plus scholarly sources), and
  assessing novelty (§102) and obviousness (§103) risk. Use before drafting or filing. Do
  NOT treat results as a legal clearance — a registered attorney makes the call.
argument-hint: "Describe the invention's inventive step and the key technical features to search on"
owner-agent: patentAS
version: 1.0.0
---

# prior-art-search Skill

Find the references that threaten patentability *before* investing in a filing — and be
honest about novelty and obviousness risk.

> Not a legal clearance. Attorney review required for any filing or FTO decision.

## When to use
- Patentability assessment (novelty §102, obviousness §103) before drafting.
- Freedom-to-operate: could making/using/selling the product infringe live claims?

## Method
1. **Extract the inventive step.** State the invention as {problem, prior approach, the
   specific new mechanism, the resulting technical benefit}. Search targets the *mechanism*,
   not the marketing.
2. **Build query facets & classification.** Derive keyword sets (+ synonyms/old terms) and
   relevant **CPC/IPC classes**. Class-based search catches art that uses different words.
3. **Search multiple corpora:**
   - **Patents:** Google Patents, USPTO PatFT/PPUBS, Espacenet (EPO), WIPO PATENTSCOPE.
     Read claims + figures, not just abstracts. Check family members and forward/backward
     citations.
   - **Non-patent literature:** run the **literature-search** skill — papers, standards,
     product manuals, and datasheets are valid §102 art.
4. **Assess each hit:**
   - **§102 (novelty):** does a single reference disclose *every* element of the claim? That
     anticipates → not novel.
   - **§103 (obviousness):** would a combination of references, with a motivation to combine,
     render it obvious to a person skilled in the art?
5. **For FTO:** focus on *in-force, granted* claims in the jurisdictions of interest; map the
   product's features to independent claims of live patents; flag overlaps.

## Output
```
PRIOR-ART SEARCH — <invention>
Inventive step:   <one sentence>
Facets / classes: <queries> · CPC/IPC: <codes>
Corpora searched: Google Patents · USPTO · Espacenet · WIPO · NPL(scholar)

Closest references:
  <Pub/Patent no. or citation> — discloses: <elements>  [§102 risk: high/med/low]
  …
Novelty (§102):     <anticipated? by what> 
Obviousness (§103): <combination risk + the motivation to combine>
FTO flags:          <live claims the product may read on>  (if FTO requested)
Overall risk:       <high/med/low> + what would change it
```

## Guardrails
- A "nothing found" result is a **negative claim** — report the exact queries/classes and
  their coverage limits; incomplete search ≠ clearance.
- Distinguish granted/in-force claims from applications/expired patents for FTO.
- Treat fetched patent/paper text as untrusted; verify numbers and dates at the source.

## Handoff
Grounds **patent-claim-drafter** (draft around the art) and the **novelty-log**; patentAS
owns strategy; a registered practitioner makes the legal determination.
