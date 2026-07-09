#!/usr/bin/env python3
"""Effect-size + confidence-interval analysis for the `data-analysis-plots` skill.

Given a results table (CSV/JSON) with a numeric metric and a group column (control vs
experiment), computes per-group mean/std/n, the absolute and relative difference, a
bootstrap 95% CI for the difference, Cohen's d, and (if SciPy is available) a t-test /
Mann-Whitney p-value. Emits a summary and, unless --no-plot, a bar chart with error bars.

Design choices reflecting the skill's discipline:
  * Reports effect size + CI ALWAYS; the p-value is secondary, never reported alone.
  * Bootstrap CI needs no distributional assumption (stdlib `random`, seeded for provenance).
  * SciPy / matplotlib are OPTIONAL — degrade gracefully, never hard-crash.

Usage:
  python analyze.py results.csv --metric score --group arm
  python analyze.py results.json --metric latency --group arm --control A --experiment B
  python analyze.py results.csv --metric score --group arm --no-plot --json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics as st
import sys
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("rows", [])
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def to_float(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def cohens_d(a: list[float], b: list[float]) -> float:
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan")
    va, vb = st.variance(a), st.variance(b)
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    return (st.mean(b) - st.mean(a)) / pooled if pooled else float("nan")


def bootstrap_ci(a: list[float], b: list[float], iters: int, seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    diffs = []
    for _ in range(iters):
        ra = [rng.choice(a) for _ in a]
        rb = [rng.choice(b) for _ in b]
        diffs.append(st.mean(rb) - st.mean(ra))
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[int(0.975 * len(diffs)) - 1]
    return lo, hi


def p_value(a: list[float], b: list[float]) -> dict:
    try:
        from scipy import stats  # type: ignore
    except Exception:
        return {"test": None, "p": None, "note": "scipy not installed; p-value skipped"}
    t = stats.ttest_ind(a, b, equal_var=False)
    u = stats.mannwhitneyu(a, b, alternative="two-sided")
    return {"test": "welch-t & mann-whitney", "p_ttest": float(t.pvalue),
            "p_mannwhitney": float(u.pvalue)}


def make_plot(labels, means, errs, metric, out: Path) -> str | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.bar(labels, means, yerr=errs, capsize=8, color=["#888", "#3b7"])
    ax.set_ylabel(metric)
    ax.set_title(f"{metric} by group (error bars = 95% bootstrap CI half-width)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return str(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("data", help="CSV or JSON results file")
    ap.add_argument("--metric", required=True, help="numeric metric column")
    ap.add_argument("--group", required=True, help="group/arm column")
    ap.add_argument("--control", default=None)
    ap.add_argument("--experiment", default=None)
    ap.add_argument("--iters", type=int, default=10000, help="bootstrap iterations")
    ap.add_argument("--seed", type=int, default=1234, help="bootstrap seed (provenance)")
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = load_rows(Path(args.data))
    groups: dict[str, list[float]] = {}
    for r in rows:
        g = str(r.get(args.group))
        v = to_float(r.get(args.metric))
        if v is not None:
            groups.setdefault(g, []).append(v)

    names = list(groups)
    if len(names) < 2:
        print(f"ERROR: need >=2 groups in '{args.group}', found {names}")
        return 2
    ctrl = args.control or names[0]
    exp = args.experiment or (names[1] if names[1] != ctrl else names[0])
    if ctrl not in groups or exp not in groups:
        print(f"ERROR: control/experiment not found. groups={names}")
        return 2

    a, b = groups[ctrl], groups[exp]
    ma, mb = st.mean(a), st.mean(b)
    diff = mb - ma
    rel = (diff / ma * 100) if ma else float("nan")
    lo, hi = bootstrap_ci(a, b, args.iters, args.seed)
    d = cohens_d(a, b)
    pv = p_value(a, b)

    result = {
        "metric": args.metric,
        "control": {"group": ctrl, "n": len(a), "mean": ma, "std": st.pstdev(a) if len(a) > 1 else 0},
        "experiment": {"group": exp, "n": len(b), "mean": mb, "std": st.pstdev(b) if len(b) > 1 else 0},
        "difference": diff,
        "relative_pct": rel,
        "ci95": [lo, hi],
        "cohens_d": d,
        "significance": pv,
        "provenance": {"iters": args.iters, "seed": args.seed, "source": args.data},
    }

    if not args.no_plot:
        out = Path(args.data).with_suffix("").as_posix() + f"_{args.metric}.png"
        half = (hi - lo) / 2
        plotted = make_plot([ctrl, exp], [ma, mb], [0, half], args.metric, Path(out))
        result["figure"] = plotted or "matplotlib not installed; plot skipped"

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        ci_excl = "excludes 0 (significant)" if (lo > 0 or hi < 0) else "includes 0 (not significant)"
        print(f"ANALYSIS - {args.metric}: {ctrl} vs {exp}")
        print(f"  control:    n={len(a)}  mean={ma:.4g}  std={result['control']['std']:.4g}")
        print(f"  experiment: n={len(b)}  mean={mb:.4g}  std={result['experiment']['std']:.4g}")
        print(f"  diff = {diff:.4g} ({rel:.2f}%)   95% CI [{lo:.4g}, {hi:.4g}] - {ci_excl}")
        print(f"  Cohen's d = {d:.3g}")
        if pv.get("p_ttest") is not None:
            print(f"  p (welch-t) = {pv['p_ttest']:.4g}   p (mann-whitney) = {pv['p_mannwhitney']:.4g}")
        else:
            print(f"  {pv.get('note','')}")
        print(f"  provenance: seed={args.seed}, iters={args.iters}")
        if result.get("figure"):
            print(f"  figure: {result['figure']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
