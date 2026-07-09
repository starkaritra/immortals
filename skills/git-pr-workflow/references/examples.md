# git-pr-workflow — worked examples

> Reference for the `git-pr-workflow` skill. Load on demand (via `skill_get_reference`) when you
> want a concrete model of a good commit message and pre-publish report. Core workflow lives in
> `../SKILL.md`.

## Good example — a commit message

```
Add bootstrap CI to the experiment analyzer

The analyzer reported only a p-value, which hides effect size and lets trivial
differences read as "significant". Add a seeded bootstrap 95% CI and Cohen's d so
every comparison carries an effect size + interval. Seed is logged for provenance.

Trade-off: bootstrap adds ~0.5s per run at 10k iters; acceptable for offline analysis.
```

Why it's good: imperative title ≤72 chars; body explains **why** (the p-value-only problem), what
changed, and the trade-off. No `Co-authored-by` AI trailer; authored as the repo owner.

## Good example — a pre-publish report (the remote gate)

```
PRE-PUBLISH REPORT
- Target:        feature/analyzer-ci → origin
- Diff summary:  2 files changed, +48 −3 (analyze.py, test_analyze.py)
- What & why:    adds bootstrap CI + Cohen's d to the analyzer; hardens the stats story.
- Commit(s):     "Add bootstrap CI to the experiment analyzer"
- Full message:  <the message above>
Awaiting your approval to push.
```

Why it's good: shows target, diff summary, prose rationale, and the exact message *before*
touching the remote — then stops and waits for explicit approval (coderAS rule 19).

## Bad example — what to avoid

```
git commit -am "updates" && git push
```

Why it's bad: vague message, stages everything blindly (possible unrelated changes/secrets),
crosses the local→remote boundary with **no** pre-publish report and no approval, and risks an
AI-authored trailer. Every one of these violates the skill's guardrails.
