---
name: data-analysis-plots
description: >
  experimentAS-family skill for turning experiment/eval results into rigorous statistics and
  publication-quality plots. Triggers on: "analyze these results", "plot my metrics", "is
  this difference significant", "make a bar chart with error bars", "compare control vs
  experiment", "effect size", "confidence interval", "variance over seeds". Owns the durable
  craft of computing effect sizes + CIs (never a bare p-value), aggregating over seeds/runs,
  correcting for multiplicity, and rendering clear figures. Use when experiment output needs
  analysis or visualization. Do NOT use it to design the experiment — that's experimentAS.
argument-hint: "Point me at the results file (CSV/JSON) and name the metric + the control/experiment columns"
---

# data-analysis-plots Skill

Turn raw run outputs into honest numbers and readable figures — effect sizes and intervals,
not decorated p-values.

## When to use
- You have experiment/eval results (CSV/JSON/DataFrame) and need statistics or plots.
- Comparing control vs experiment (A/B, ablation, arm-vs-arm).
- Reporting variance across seeds/runs.

## Analysis discipline (from experimentAS methodology)
1. **Sanity first.** Check row counts per arm (sample-ratio mismatch), missing values, and
   obvious outliers before any test. Run an A/A check if the harness supports it.
2. **Aggregate over seeds/runs — never a single run.** Report mean ± std and the number of
   runs. For ML/eval, variance across seeds is part of the result.
3. **Effect size + confidence interval, always.** Report the difference (absolute and
   relative), a 95% CI, and the effect-size measure (Cohen's d / Cliff's delta as
   appropriate). State *practical* significance, not just statistical.
4. **Then the test.** Use the pre-committed test (t-test/Mann–Whitney/bootstrap as fits the
   data); report the statistic and p-value **alongside** the CI, never instead of it.
5. **Correct for multiplicity.** Bonferroni for a few critical tests; Benjamini–Hochberg
   (FDR) for many. State which and why.
6. **Do not p-hack.** No peeking-driven stopping; label any post-hoc analysis as exploratory.

## Plotting
- Prefer `matplotlib`/`seaborn` (Python) or the repo's existing plotting stack.
- Bar/point plots **must show error bars** (CI or std, labeled). Never a bare mean bar.
- Use clear axis labels with units, a legend, and a caption stating n, the error-bar meaning,
  and the test. Save as vector (SVG/PDF) for papers; PNG for quick looks.
- One idea per figure; annotate the effect size on the plot when it's the headline.

## Output
```
ANALYSIS — <metric>, control vs experiment
n:            control=<n>, experiment=<n>, seeds=<k>
Point est.:   control=<μ±σ>, experiment=<μ±σ>
Effect:       Δ=<abs> (<rel>%), 95% CI [<lo>, <hi>], d=<effect size>
Test:         <name>, stat=<..>, p=<..>  (multiplicity: <method>)
Verdict:      <practically significant? y/n> — <one line>
Figure:       <path to saved plot>
```

## Guardrails
- Never report a bare p-value or "significant" without an effect size and CI.
- State assumptions of each test; switch to non-parametric when they're violated.
- Log provenance: data file hash, seeds, code commit, and the analysis parameters.

## Handoff
**experimentAS** owns the design, pre-registration, and causal interpretation; this skill
produces the numbers and figures it reports.
