# citation-verify — worked examples

> Reference for the `citation-verify` skill. Load on demand (via `skill_get_reference`) when you
> want a concrete model of a good verification report. The core workflow lives in `../SKILL.md`.

## Good example — a verification report

Input: `refs.bib` with 4 entries. After running `assets/resolve_refs.py refs.bib`:

```
CITATION VERIFICATION — refs.bib   (4 entries)
✓ verified:      2
⚠ metadata-fix:  vaswani2017 — year: bib says 2016, Crossref says 2017
✗ UNVERIFIED:    smith2023deep — could not resolve "Deep Nets for Everything";
                 no DOI/arXiv, no Crossref title match → likely hallucinated
⚠ claim-review:  §3, cite{he2016} — claim: "first to exceed human accuracy on ImageNet";
                 cited work is about residual connections, not the human-accuracy claim

Fix order (UNVERIFIED first):
  1. smith2023deep — remove or replace; do not cite unverifiable work in a submission.
  2. vaswani2017   — correct year 2016 → 2017.
  3. he2016 (§3)   — re-cite the correct source for the human-accuracy claim, or soften it.
```

Why it's good: leads with the sink-the-submission issue (UNVERIFIED), separates a *metadata* fix
from a *claim–citation* mismatch, and gives an ordered, actionable fix list. Every status is
backed by what the source actually said.

## Bad example — what to avoid

```
I checked your citations and they mostly look fine. Vaswani might have a wrong year.
The Smith paper I couldn't find but it's probably okay.
```

Why it's bad: no per-entry status, treats an unresolvable (likely hallucinated) citation as
"probably okay" (the single most dangerous error), no evidence, no fix order, and no distinction
between metadata vs claim problems.
