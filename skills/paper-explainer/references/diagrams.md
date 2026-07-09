# Paper Explainer — diagram design system

> Reference for the `paper-explainer` skill. Load when rendering SVG diagrams.
> The core workflow lives in `../SKILL.md`.

## Diagram Design System

All diagrams are inline SVG. The following rules apply to every diagram in the exported HTML.

### SVG canvas defaults

- `viewBox="0 0 W H"` — choose W/H to give natural aspect ratio. Never use `width`/`height` attributes; let CSS control sizing.
- `background: var(--surface-1)` applied via a `<rect x="0" y="0" width="100%" height="100%" fill="…"/>` as first child.
- `font-family="Inter, system-ui, sans-serif"` on the root `<svg>` element.
- Padding: 24px inset from edge to outermost content.

### Shared SVG `<defs>` (include once in each diagram)

```svg
<defs>
  <!-- Arrow markers — two weights -->
  <marker id="arr-sm" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto">
    <path d="M0,0.5 L0,6.5 L6,3.5 z" fill="var(--text-3)" opacity="0.8"/>
  </marker>
  <marker id="arr-md" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0.5 L0,7.5 L7,4 z" fill="var(--accent)"/>
  </marker>
  <marker id="arr-green" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0.5 L0,7.5 L7,4 z" fill="var(--green)"/>
  </marker>
  <marker id="arr-purple" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
    <path d="M0,0.5 L0,7.5 L7,4 z" fill="var(--purple)"/>
  </marker>

  <!-- Drop shadow filter -->
  <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000" flood-opacity="0.35"/>
  </filter>

  <!-- Glow filter (for highlighted / contribution nodes) -->
  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="4" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>

  <!-- Gradient fills for node types -->
  <linearGradient id="grad-accent" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#4f8ef7" stop-opacity="0.25"/>
    <stop offset="100%" stop-color="#4f8ef7" stop-opacity="0.08"/>
  </linearGradient>
  <linearGradient id="grad-green" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#34d399" stop-opacity="0.22"/>
    <stop offset="100%" stop-color="#34d399" stop-opacity="0.06"/>
  </linearGradient>
  <linearGradient id="grad-purple" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#a78bfa" stop-opacity="0.22"/>
    <stop offset="100%" stop-color="#a78bfa" stop-opacity="0.06"/>
  </linearGradient>
  <linearGradient id="grad-orange" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#fb923c" stop-opacity="0.22"/>
    <stop offset="100%" stop-color="#fb923c" stop-opacity="0.06"/>
  </linearGradient>
  <linearGradient id="grad-surface" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#1a2235" stop-opacity="1"/>
    <stop offset="100%" stop-color="#111827" stop-opacity="1"/>
  </linearGradient>
</defs>
```

### Node types

| Node role | Fill | Stroke | Stroke-width | Filter | Text color |
|---|---|---|---|---|---|
| **Contribution** (paper's main idea) | `url(#grad-accent)` | `var(--accent)` | `2px` | `glow` | `var(--accent)` |
| **Mechanism / method** | `url(#grad-green)` | `var(--green)` | `1.5px` | `shadow` | `var(--green)` |
| **Prerequisite / context** | `url(#grad-surface)` | `var(--border-2)` | `1px` | — | `var(--text-2)` |
| **Constraint / limitation** | `url(#grad-orange)` | `var(--orange)` | `1.5px` | — | `var(--orange)` |
| **Downstream / spawned work** | `url(#grad-purple)` | `var(--purple)` | `1px` | — | `var(--purple)` |
| **Emergent / warning** | dark-red tint | `var(--red)` | `1.5px` | — | `var(--red)` |

All nodes: `rx="10"` (rounded corners), `filter` as specified, minimum height 44px, minimum width 140px.

Node interior: two lines of text — **bold name** (`font-size: 12`, `font-weight: 700`) and **short descriptor** (`font-size: 10`, `opacity: 0.75`) — both `text-anchor: middle`.

### Edge (arrow) styles

| Edge meaning | Stroke | Stroke-width | Dash | Marker |
|---|---|---|---|---|
| Primary relationship | `var(--accent)` | `1.5` | solid | `arr-md` |
| Secondary / supporting | `var(--text-3)` | `1` | solid | `arr-sm` |
| Dependency / requirement | `var(--orange)` | `1.5` | `5,3` dashed | `arr-sm` |
| Downstream / spawned | `var(--purple)` | `1` | `4,3` dashed | `arr-purple` |
| Negative / contradiction | `var(--red)` | `1` | `3,3` dashed | `arr-sm` |

Edge labels: `font-size: 9`, `fill: var(--text-3)`, placed at midpoint, `text-anchor: middle`. For curved edges use `<path>` with a quadratic Bézier (`Q`) rather than straight `<line>` where paths would otherwise cross.

### Layout guidelines

- **Central contribution node** goes in the visual centre of the diagram.
- **Mechanism nodes** cluster to the left of the contribution.
- **Task / application nodes** fan out to the right.
- **Prerequisite nodes** sit above.
- **Constraint / limitation nodes** sit below.
- **Downstream work** goes in the bottom-left corner.
- Minimum node separation: 30px horizontal, 20px vertical.
- Include a small **legend box** (bottom-left or bottom-right) when the diagram uses more than three node types. Legend: 12×12 px color swatches with labels.

### Diagram-specific additional rules

**Knowledge graph (Step 2e / Step 5 closing):**
- Minimum 5 nodes for a typical paper; aim for 8–12 for a full-length paper.
- Every node must have at least one inbound or outbound edge.
- Prefer curved `<path>` edges (quadratic Bézier) over straight lines for dense graphs.
- Label all edges.

**Architecture / method diagrams (Section walkthrough):**
- Use layered left-to-right flow for pipelines.
- Data flow arrows use `arr-md`; control flow uses `arr-sm` dashed.
- Group related components with a faint enclosing `<rect>` with a label at the top-left (`font-size: 10`, `fill: var(--text-3)`, `font-style: italic`).

**Comparison / ablation diagrams:**
- Prefer Chart.js horizontal bar charts over SVG for numeric data.
- Use SVG only for qualitative comparisons (e.g., a method overview side-by-side).

**Equation decomposition diagrams:**
- Show the equation at top in a shaded box.
- Draw callout lines from sub-expressions to plain-English labels below.
- Callout lines: `stroke: var(--text-3); stroke-dasharray: 3,2`.

---
