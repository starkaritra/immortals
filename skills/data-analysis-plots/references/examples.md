# data-analysis-plots — worked examples

> Reference for the `data-analysis-plots` skill. Load on demand (via `skill_get_reference`) when
> you want a concrete model of a good analysis report. Core workflow lives in `../SKILL.md`.

## Good example — an analysis report

After `python assets/analyze.py results.csv --metric score --group arm`:

```
ANALYSIS - score: control vs experiment
  control:    n=200  mean=0.712  std=0.041
  experiment: n=205  mean=0.738  std=0.039
  diff = 0.026 (3.65%)   95% CI [0.018, 0.034] - excludes 0 (significant)
  Cohen's d = 0.65   (medium effect)
  p (welch-t) = 0.0003   p (mann-whitney) = 0.0006   (multiplicity: BH over 3 metrics)
  Verdict: practically significant — +3.7% relative, CI excludes 0, medium effect.
  provenance: seed=1234, iters=10000, source=results.csv@sha256:ab12…
  figure: results_score.png (bars ± 95% bootstrap CI)
```

Why it's good: reports **effect size + CI first**, the p-value only *alongside* it (never alone),
states multiplicity correction, gives a practical-significance verdict (not just "p<0.05"), and
logs full provenance (seed, iters, data hash) so the number is reproducible.

## Bad example — what to avoid

```
The experiment is better, p = 0.0003, so it's statistically significant. Ship it.
```

Why it's bad: a bare p-value with no effect size, no CI, no sample sizes, no variance, no
multiplicity correction, no provenance, and it jumps straight to a ship decision — exactly the
"significant p, trivial effect" trap the skill exists to prevent.
