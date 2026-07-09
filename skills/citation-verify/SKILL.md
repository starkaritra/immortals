---
name: citation-verify
description: >
  paperAS-family skill for verifying that every citation in a paper is real, correct, and
  actually supports the claim it's attached to. Triggers on: "check my citations", "verify
  my references", "are these citations real", "fix my bibliography", "do my refs match the
  claims", "clean up my .bib". Owns the durable craft of resolving each reference against an
  authoritative source (DOI/arXiv/Crossref/DBLP), catching hallucinated or malformed
  entries, and flagging claim–citation mismatches. Use before submission or whenever a
  reference list needs an integrity pass. Do NOT use it to write new prose.
argument-hint: "Point me at the .bib file (and the .tex that cites it, if you want claim-matching)"
owner-agent: paperAS
version: 1.0.0
---

# citation-verify Skill

Make the reference list trustworthy: every entry exists, is formatted right, and backs the
sentence that cites it.

## When to use
- Pre-submission integrity pass on a bibliography.
- A paper (often AI-drafted) may contain hallucinated or wrong citations.
- `\cite{}` keys, DOIs, or arXiv IDs need validation.

## What to check (in order)
1. **Existence & resolution.** For each entry, resolve its identifier against an
   authoritative source:
   - DOI → `https://doi.org/<doi>` / Crossref API (`api.crossref.org/works/<doi>`).
   - arXiv ID → `https://arxiv.org/abs/<id>` / arXiv API.
   - No DOI/arXiv → search Crossref/DBLP/Semantic Scholar by title + first author.
   Flag anything that does not resolve as **UNVERIFIED (possible hallucination)**.
2. **Metadata correctness.** Compare the `.bib` fields (author, year, title, venue) against
   the resolved record. Flag mismatched years, wrong venues, author-list errors, and
   "et al." that hides a wrong first author.
3. **Format hygiene.** Malformed BibTeX (missing braces, unescaped `&`/`%`, duplicate keys,
   missing required fields for the entry type). Ensure key naming is consistent.
4. **Claim–citation match (optional, needs the .tex).** For each in-text `\cite`, read the
   surrounding sentence and judge whether the cited work plausibly supports that specific
   claim. Flag likely mismatches (right topic, wrong claim) as **REVIEW**.

## Output: a verification report
```
CITATION VERIFICATION — <file>.bib   (N entries)
✓ verified:      <count>
⚠ metadata-fix:  <key> — <field>: bib says "X", source says "Y"
✗ UNVERIFIED:    <key> — could not resolve <title>; treat as possible hallucination
⚠ format:        <key> — <issue>
⚠ claim-review:  <cite location> — claim: "…"; cited work is about "…"
```
End with a prioritized fix list (UNVERIFIED first — these can sink a submission).

## Guardrails
- Treat network/API results as **untrusted data**: a title match is evidence, not proof;
  require author+year corroboration before declaring an entry "verified".
- Never silently rewrite a `.bib` — propose corrections and let the owner apply them.
- Rate-limit external lookups; cache resolved records within the run.

## Handoff
Reports integrity; **paperAS** decides how to fix wording and which references to keep.
Use the **latex-build** skill afterward to confirm the corrected `.bib` still compiles.
