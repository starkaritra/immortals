# Paper Explainer — HTML output spec

> Reference for the `paper-explainer` skill. Load when building the HTML artifact.
> The core workflow lives in `../SKILL.md`.

### What the HTML file must contain

The exported file is a **complete, standalone reproduction** of the chat explanation. Every step, every equation, every diagram, every chart that appeared in the chat must appear in the HTML — nothing omitted, nothing summarized.

Include:
1. **Header block** — title, authors, venue, year, arXiv/DOI link, generated-on date.
2. **Table of contents** — `<nav aria-label="Table of contents">` with anchor links to every Step heading and major subsection.
3. **All five explanation steps** — Big Picture table, Background (2a–2e), Section-by-Section Walkthrough, Results & Experiments, Synthesis & Closing.
4. **Every equation** — rendered with KaTeX (CDN).
5. **Every conceptual SVG diagram** — knowledge graphs, architecture diagrams, equation visualizations.
6. **Every results chart** — rendered as an interactive Chart.js chart (CDN), with a plain `<table>` of the same data adjacent for fallback/print.
7. **Original figure thumbnails** — when the paper's figures are freely accessible (e.g. arXiv), embed small clickable thumbnails of originals next to your conceptual redraws.
8. **Footer** — source URL, PDF conversion tip, note that first load needs internet for KaTeX/Chart.js.

### Delivery: write directly to disk

After producing the HTML content, **write the file to disk** at:
- Windows: `C:\Users\<user>\Downloads\<paper-slug>.html`
- macOS/Linux: `~/Downloads/<paper-slug>.html`

Where `<paper-slug>` is the paper's short title in kebab-case (e.g. `rag-knowledge-intensive-nlp.html`).

Use the available file-write tool. Then post a short summary in chat confirming the path and listing what was exported, e.g.:

> Wrote 12 sections · 7 equations · 3 diagrams · 2 interactive charts · 1 figure thumbnail to `C:\Users\...\Downloads\rag-knowledge-intensive-nlp.html`

**Do NOT paste the full HTML into the chat** — the file on disk is the deliverable. If file-write tools are unavailable, fall back to a single fenced ```html code block and instruct the user to save it manually.

### KaTeX (math) — CDN-loaded with auto-render

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]});"></script>
```

Then write equations inline using `$...$` (inline) and `$$...$$` (display). Auto-render handles them — no per-equation `<script>` tag needed.

### Charts — Chart.js via CDN

For every numeric comparison in the Results section (model scores, training curves, ablations, hot-swap results, generation diversity), render an **interactive Chart.js chart**, not a static SVG.

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<div style="max-width:720px;margin:1rem auto"><canvas id="chart-1"></canvas></div>
<script>
new Chart(document.getElementById('chart-1'), {
  type: 'bar',
  data: { labels: [...], datasets: [{ label: '...', data: [...], backgroundColor: '...' }] },
  options: { responsive: true, plugins: { title: { display: true, text: '...' } } }
});
</script>
```

Rules:
- Always also include a plain `<table>` of the same data directly above the chart. Print and screen-reader fallback.
- Use a consistent color palette across all charts — assign each model/method a stable color. Define palette as CSS variables.
- Set `aria-label` on each `<canvas>` describing the chart's content.
- Pick chart type by data: bar for cross-model comparison; line for training curves or "vs. K documents"; grouped bar for multi-metric comparison.

### Figures — conceptual SVG redraw + original thumbnail

For each figure the paper contains:

1. Produce a **clean conceptual SVG redraw** illustrating the same idea — the primary visual, readable and consistent with the diagram style.
2. **Also embed a small clickable thumbnail** of the original figure when accessible (e.g. `https://arxiv.org/html/XXXX.XXXXX/x1.png`).

Use `<figure>` semantics:

```html
<figure>
  <svg role="img" aria-label="..."><title>...</title>...</svg>
  <figcaption>
    Conceptual redraw of Figure N from the paper.
    <a href="[original-url]" target="_blank" rel="noopener">
      <img src="[original-url]" alt="Original Figure N"
           style="max-width:220px;border:1px solid var(--border);border-radius:4px;margin-top:8px"/>
    </a>
    <br><small>Source: Fig. N of <a href="[paper-url]">[paper title]</a></small>
  </figcaption>
</figure>
```

Only embed thumbnails when source is freely accessible (arXiv, OA journals). Skip for paywalled papers and note the omission in the figcaption.

### Glossary tooltips

Every term that was formally defined in **Step 2 — Background** (e.g. "retrieval-augmented generation", "BM25", "perplexity") gets a `<dfn>` wrapper on first mention and a hover/focus tooltip everywhere else in the document.

```html
<!-- first mention, in Background -->
<dfn id="def-bm25" title="A sparse-lexical retrieval scoring function based on term frequency and inverse document frequency.">BM25</dfn>

<!-- later mentions, anywhere -->
<abbr class="gloss" data-term="bm25">BM25</abbr>
```

Include a small CSS + JS snippet that:
- Underlines `.gloss` with a dotted line.
- On hover/focus, shows the definition from the matching `<dfn>` element as a `<div role="tooltip">` positioned below.
- Falls back to the native `title` attribute if JS is disabled.

Build a `<dl>` glossary section at the bottom of the article (before the footer) auto-listing every `<dfn>`, so the print/PDF version retains the definitions.

### Back-to-top, no-JS warning, version footer

Add a floating back-to-top button that appears after the user scrolls past the first viewport:

```html
<a href="#top" id="back-to-top" aria-label="Back to top"
   style="position:fixed;bottom:1.5rem;right:1.5rem;display:none;
          padding:.6rem .8rem;border-radius:50%;background:var(--accent);
          color:var(--bg);text-decoration:none;box-shadow:0 2px 6px rgba(0,0,0,.2)">↑</a>
<script>
  const btt = document.getElementById('back-to-top');
  addEventListener('scroll', () => { btt.style.display = scrollY > 600 ? 'block' : 'none'; });
</script>
```

Immediately after `<body>`, include a `<noscript>` banner:

```html
<noscript>
  <div style="padding:1rem;background:#fff3cd;border:1px solid #ffc107;border-radius:6px;margin-bottom:1rem">
    <strong>JavaScript is disabled.</strong> Equations (KaTeX) and result charts (Chart.js) will not render.
    Each chart has a plain data table directly above it, and every equation appears as raw LaTeX between
    <code>$$...$$</code> markers. The rest of the document is fully readable.
  </div>
</noscript>
```

Footer must include a small machine-parseable version block:

```html
<footer>
  <p>Source: <a href="[paper-url]">[paper title]</a></p>
  <p>To convert to PDF: open in browser → File → Print → Save as PDF.
     First load needs internet for KaTeX/Chart.js; cached thereafter.</p>
  <p><small>
    Generated by <code>paper-explainer</code> skill
    v<span data-skill-version>1.2.0</span>
    on <time datetime="[ISO-8601]">[human date]</time>
    · Paper source: <code>[arXiv ID / DOI]</code>
  </small></p>
</footer>
```

Bump `data-skill-version` whenever the export template materially changes; users can diff two exports of the same paper to spot stale outputs.

### File structure & styling

- Single `.html` file. External resources: only KaTeX + Chart.js CDNs (allowed) and arXiv figure thumbnails (when present).
- `<article>` root, `max-width: 860px`, centered.
- Semantic HTML: `<article>`, `<section>`, `<figure>`, `<nav>`, `<h1>`–`<h4>` hierarchy.
- Every `<svg>` and `<canvas>` gets `role="img"`, `aria-label="..."`. Every `<svg>` has a `<title>` first child.
- `@media print` rules: hide `<nav>` and `#back-to-top`, expand all `<details>`, prevent page breaks inside `<figure>` and Deep Dive callouts.

#### Typography

Load **Inter** from Google Fonts as the body font; **JetBrains Mono** for code and equation labels. Both are free and load in a single `<link>` call. Fall back to system fonts if offline:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
```

Set body `font-size: 16px`, `line-height: 1.75`, `letter-spacing: -0.01em`. Headings use `font-weight: 700`, `letter-spacing: -0.02em`. Code uses JetBrains Mono at `0.875em`.

#### CSS Design Tokens (required variables)

Define these in `:root` — use them everywhere, never hardcode:

```css
:root {
  /* Surfaces */
  --bg:          #0a0e17;   /* page background — deep navy-black */
  --surface-1:   #111827;   /* cards, sidebars */
  --surface-2:   #1a2235;   /* nested cards, code blocks */
  --surface-3:   #1e2d45;   /* hover states, active rows */

  /* Borders */
  --border-1:    rgba(255,255,255,0.06);
  --border-2:    rgba(255,255,255,0.10);

  /* Accent palette — cool-blue primary, vivid secondaries */
  --accent:      #4f8ef7;   /* primary CTA, links */
  --accent-glow: rgba(79,142,247,0.18);
  --green:       #34d399;
  --orange:      #fb923c;
  --purple:      #a78bfa;
  --red:         #f87171;
  --yellow:      #fbbf24;

  /* Text */
  --text-1:      #f0f4ff;   /* headings */
  --text-2:      #94a3b8;   /* body prose */
  --text-3:      #4b5e78;   /* muted labels */

  /* Geometry */
  --radius-sm:   6px;
  --radius-md:   10px;
  --radius-lg:   16px;

  /* Shadows */
  --shadow-sm:   0 1px 3px rgba(0,0,0,0.4);
  --shadow-md:   0 4px 16px rgba(0,0,0,0.5);
  --shadow-lg:   0 8px 32px rgba(0,0,0,0.6);

  /* Transitions */
  --transition:  0.18s cubic-bezier(0.4,0,0.2,1);
}
```

Light theme (inside `@media (prefers-color-scheme: light)`):

```css
:root {
  --bg: #f8faff; --surface-1: #ffffff; --surface-2: #f1f5fd; --surface-3: #e8effa;
  --border-1: rgba(0,0,0,0.07); --border-2: rgba(0,0,0,0.12);
  --accent: #2563eb; --accent-glow: rgba(37,99,235,0.12);
  --text-1: #0f172a; --text-2: #334155; --text-3: #94a3b8;
}
```

#### Visual polish rules

- **Cards & sections:** `background: var(--surface-1)`, `border: 1px solid var(--border-1)`, `border-radius: var(--radius-md)`, `box-shadow: var(--shadow-sm)`. On hover (`section:hover` not needed, but interactive cards use `var(--shadow-md)`).
- **Paper header:** give it a subtle gradient top border — `border-top: 3px solid; border-image: linear-gradient(90deg, var(--accent), var(--purple)) 1`.
- **Step headings (`h2.step`):** add a left accent bar — `border-left: 3px solid var(--accent); padding-left: 0.75rem`.
- **Reading progress bar:** a thin 2px bar at the very top of the viewport that fills as the user scrolls, using `position: fixed; top: 0; left: 0; height: 2px; background: linear-gradient(90deg, var(--accent), var(--purple))`.
- **Equation blocks:** soft glow border — `border: 1px solid var(--accent-glow); box-shadow: 0 0 0 3px var(--accent-glow)`.
- **Deep Dive callouts:** `border-left: 3px solid var(--purple); background: linear-gradient(90deg, rgba(167,139,250,0.06) 0%, transparent 60%)`.
- **Table rows:** `transition: background var(--transition)` on hover → `var(--surface-3)`.
- **Badges:** pill shape (`border-radius: 999px`), micro font (`font-size: 0.72rem`, `letter-spacing: 0.06em`, `font-weight: 700`).
- **`<code>` inline:** `background: var(--surface-2); border: 1px solid var(--border-2); font-family: 'JetBrains Mono', monospace`.
- **Links:** `color: var(--accent); text-underline-offset: 3px`. Hover adds a `text-shadow: 0 0 12px var(--accent-glow)` glow.
- **Tooltips:** `backdrop-filter: blur(8px); background: rgba(17,24,39,0.9)` for a frosted-glass effect.
- **Back-to-top button:** `background: linear-gradient(135deg, var(--accent), var(--purple)); box-shadow: var(--shadow-md)`.

#### Reading progress bar implementation

```html
<div id="progress-bar" style="position:fixed;top:0;left:0;width:0%;height:2px;
     background:linear-gradient(90deg,var(--accent),var(--purple));z-index:1000;
     transition:width 0.1s linear" role="progressbar" aria-hidden="true"></div>
<script>
  const pb = document.getElementById('progress-bar');
  window.addEventListener('scroll', () => {
    const pct = (scrollY / (document.body.scrollHeight - innerHeight)) * 100;
    pb.style.width = Math.min(pct, 100) + '%';
  });
</script>
```

---
