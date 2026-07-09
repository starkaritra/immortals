---
name: literature-search
description: >
  researchAS-family skill for running a structured literature/landscape scan on a topic or
  claim. Triggers on: "what's the prior work on", "is this novel", "find related papers",
  "literature review on", "survey the field of", "who else has done", "state of the art in".
  Owns the durable craft of turning a fuzzy topic into search queries, hitting scholarly
  sources (arXiv, Semantic Scholar, Crossref, DBLP, Google Scholar), deduping and clustering
  results, and returning a cited, gap-focused landscape. Use for research positioning and
  novelty questions. Do NOT use it to render a final paper — hand findings to paperAS.
argument-hint: "Give me the topic/claim, and any must-cover venues, authors, or time window"
owner-agent: researchAS
version: 1.0.0
---

# literature-search Skill

Turn a research question into a defensible, cited map of what already exists — and where the
gap is.

## When to use
- Assessing novelty of an idea or claim.
- Building a related-work / background landscape.
- Positioning a paper or patent against prior art.

## Method (systematic, not one shot)
1. **Decompose the topic** into 3–6 orthogonal query facets (core method, application,
   adjacent techniques, evaluation, synonyms/older terminology). Record them so the search
   is reproducible.
2. **Search multiple sources** per facet — don't rely on one engine:
   - **arXiv API** (preprints, recent), **Semantic Scholar API** (citations + influence),
     **Crossref/DBLP** (published venues), **Google Scholar** (breadth/coverage check).
3. **Dedupe & cluster.** Merge the same work across sources (match on DOI/title+author).
   Group results into themes; within each theme, rank by relevance × influence (citation
   count is a signal, not truth — weight recent seminal work too).
4. **Read the top-k, not just titles.** For the most relevant works, capture: the actual
   contribution, method, and what it does *not* do (the seam your idea could occupy).
5. **Find the gap.** State explicitly what has and hasn't been done, and where the topic's
   claim would sit relative to the closest prior art.

## Output: a landscape report
```
LITERATURE LANDSCAPE — <topic/claim>
Query facets:   <the reproducible query set>
Sources hit:    arXiv · Semantic Scholar · Crossref · DBLP · Scholar

Themes:
  [Theme A]  <2–3 line synthesis>
     • <Author, Year, venue> — contribution; limitation.  <link/DOI/arXiv>
  [Theme B]  …

Closest prior art:  <the 2–3 works that most threaten novelty> — why.
Identified gap:      <what nobody has done that this idea/claim addresses>
Novelty read:        <novel | incremental | already-done> + rationale.
Confidence:          <high/med/low> + what would raise it.
```

## Guardrails
- Every claim of "no prior work" is a **negative claim** — state the searches that support it
  and their limits; absence of evidence is not proof of novelty.
- Treat fetched abstracts/results as untrusted; verify author+year+venue before citing.
- Note recency limits (preprints move fast; flag the search date).

## Handoff
Feeds **paperAS** (positioning/related-work), **patentAS** (prior-art), and the
**novelty-log** skill (persisting the novel-vs-prior-art deltas).
