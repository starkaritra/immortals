---
name: discovery-log
description: >
  discoverAS-family skill for keeping a lightweight, append-only markdown lab notebook of a
  discovery effort — so every session's thinking (questions, hypotheses, tournament outcomes,
  verdicts, dead-ends, next moves, handoffs) is recorded in one place the owner can revisit
  without re-reading code or re-running the lab. Triggers on: "log this session", "update the
  discovery log", "discovery-log.md", "write up what we explored", "lab notebook", "where did
  we land last time". Owns the durable craft of a chronological, revisitable discovery trail
  that links to the fuller [IDEA-NNN] entries. Keep it lightweight — a few bullets per session.
argument-hint: "Point me at discovery-log.md, or tell me the session's question and what we concluded"
owner-agent: discoverAS
requires: []
version: 1.0.0
---

# discovery-log Skill

Keep an honest, chronological, **lightweight** record of a discovery effort — one append-only
markdown file, newest session on top — so the owner (or another agent) can pick the thread back
up months later and see exactly *how the thinking moved*, including the ideas that died.

This is the human-readable trail; the queryable graph lives in **kgraph** and the full detail of
any single idea lives in `ideas.md` as `[IDEA-NNN]`. The log is the **index that ties them
together**, not a place to duplicate them.

## When to use
- At the **end of every discoverAS session** (Definition-of-Done item), and whenever a thread
  meaningfully resolves mid-session.
- When resuming work: read the top of the log first to reload where the lab last landed.
- Skip only for a throwaway one-off question that produces nothing worth revisiting.

## The file (`discovery-log.md`)
Location: repo root (or the repo's existing notebook path — adopt it rather than adding a rival
file). Append-only; **newest entry on top**, directly under the header.

**Header (write once, on creation):**
```
# Discovery Log — <project>
> Append-only lab notebook. Newest entry on top. Each block = one session's thinking.
> Full hypotheses live in ideas.md as [IDEA-NNN]; this log is the chronological trail that links them.
```

**Per-session block (≈ 6–8 short bullets — keep it lightweight):**
```
## <YYYY-MM-DD HH:MM> · <one-line session title> · mode: <engagement mode>
- Question: <what we were chasing, one line>
- Explored: <hypotheses considered — link [IDEA-NNN] for the ones worth keeping>
- Tournament: <which idea won and the one-line why (explanatory power / falsifiability / novelty / parsimony / tractability)>
- Verdict: <what survived · what died · confidence [Low/Med/High] + the one thing that would change it>
- Next move: <the single sharpest next action>
- Handoffs: <→researchAS / →experimentAS / →coderAS / →discussAS, with the specific ask>
- Meta-review: <recurring pattern / blind spot / winning move noticed this session — optional>
```

## Method
1. **On resume, read first.** Load the top few blocks (and any `Next move`) before generating —
   don't re-explore ground the log shows is already walked or already dead.
2. **Log at the end of the session.** Summarize the session into one block; prepend it under the
   header (newest on top). Keep it to a handful of lines.
3. **Link, don't duplicate.** If the session produced a genuinely new hypothesis, write the full
   `[IDEA-NNN]` in `ideas.md` and just reference the ID here.
4. **Record dead-ends too**, with *why* they died — the log's value is the honest history,
   failures included.
5. **Keep it consistent with kgraph.** When structure changed, update the kgraph map as well; the
   log is the prose trail, kgraph is the graph. Neither should drift ahead of reality.

## Output
- The maintained `discovery-log.md` (create with the header if absent).
- On request, a one-line "where we are" digest folded from the most recent blocks.

## Guardrails
- **Append-only** — never rewrite or delete a past entry; supersede it with a new dated block.
- **Lightweight** — if a block grows past ~8 bullets, push detail into `[IDEA-NNN]` and link it.
- **No invented evidence** — a logged claim carries the same evidence tags (`[known]/[believed]/
  [guess]`) and provenance discipline as the rest of discoverAS; the log records uncertainty, it
  doesn't launder it into fact.
- **No secrets/PII/confidential third-party data** in the log.

## Handoff
Indexes the discovery trail for **discoverAS**; the `Handoffs` line points concrete asks at
**researchAS** (prior art), **experimentAS** (test), **coderAS** (build/sim), and **discussAS**
(pursue-or-not). Complements the **novelty-log** skill: `novelty.md` tracks *what is new vs prior
art*; `discovery-log.md` tracks *how we got there, session by session*.
