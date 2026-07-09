# references/layouts.md — Poster layout vocabulary & design rules

The layout patterns to offer in Phase 3, and the poster-grade writing/design rules to
enforce in Phase 4. Match the choice to the **venue history** (Phase 2) and the paper's
**result-type**, not to fashion.

## Layout patterns

### 1. #betterposter "big-finding" (Mike Morrison style)
```
+----------------------------------------------------+
|  TITLE BAR · authors · affils · logo · QR          |
+------------------+-------------------+-------------+
|  ammo bar:       |                   |  ammo bar:  |
|  background,     |  THE ONE FINDING  |  details,   |
|  methods         |  (huge, plain     |  data, QR,  |
|  (small)         |   sentence)       |  refs       |
+------------------+-------------------+-------------+
```
- **Best for**: high foot-traffic venues, a single crisp takeaway, eye-from-2m readability.
- **Watch**: some traditional fields/reviewers still expect a dense classic poster — check
  the venue history before defaulting here.

### 2. Classic 3-column (academic standard)
```
+----------------------------------------------------+
|  TITLE BAR · authors · affils · logo               |
+-------------+-------------+-------------+----------+
| Intro/      | Method      | Results     | Concl/   |
| Motivation  | (diagram)   | (table/plot)| Future   |
| Related work|             |             | Refs/QR  |
+-------------+-------------+-------------+----------+
```
- **Best for**: dense technical content, methods-heavy work, reviewers who read closely.
- **Watch**: easy to overfill — enforce the text budget hard.

### 3. 2-column hybrid
- Left column narrative (problem→method), right column evidence (results→takeaway), a bold
  finding strip across the top. Good middle ground between #1 and #2.

### 4. Result-type-led variants (pick by what the paper *shows*)
- **Vision / qualitative**: lead with a **results grid** of example outputs; method diagram
  secondary. (Common at CVPR/ICCV/ECCV.)
- **Benchmark / empirical ML**: a single hero **table or bar chart** center; ablation small.
- **Theory**: one **boxed theorem/result** center-left, proof sketch as a labeled flow.
- **Systems / NLP pipeline**: a horizontal **architecture diagram** spanning the top, eval
  below.

## Poster-grade writing rules (Phase 4)
- **One finding rule**: the largest non-title text is a single plain sentence — the answer,
  not the problem.
- **Problem ≠ finding ≠ impact**: problem = why care; finding = what we found; impact =
  what it unlocks. Never collapse them.
- **Figures over prose**: a diagram/plot beats a paragraph. Aim majority visual.
- **Budget**: target very low total word count; every section ≤ a few short bullets. Cut,
  don't shrink.
- **Trace every number** to a paper figure/table; don't retype large tables — show the key
  rows or point at the source.
- **Title**: readable, not the verbatim 18-word paper title if a tighter version reads
  better from 5 m (keep it faithful).

## Design rules
- **Palette**: 2–3 colors, high contrast, **colorblind-safe** by default (e.g. Okabe–Ito or
  ColorBrewer "safe"). Honor institution brand colors if supplied.
- **Fonts**: clean sans-serif (Helvetica/Arial/Lato/Source Sans); meet the size budget in
  `references/specs.md`. One display font + one body font max.
- **Whitespace**: generous; it guides the eye and signals confidence. Don't fill every cm.
- **Alignment & grid**: align blocks to a column grid; consistent gutters.
- **QR code**: link to code/paper/project; place near the title or in the lower corner.
- **Logos**: institution/venue logos in the title bar; keep them small and aligned.
- **Accessibility**: contrast ≥ WCAG AA for body text; add alt text for any digital version.
