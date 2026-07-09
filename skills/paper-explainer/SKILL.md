---
name: paper-explainer
description: "Use when a user shares an arXiv/DOI/journal URL and wants a paper explained, summarized, broken down, or ELI5. Also triggers on: explain this paper, I don't understand this research, walk me through, what does this paper say, explain this like a student. Trigger even on a bare URL if it looks like a research paper. Do NOT use for blog posts or news articles."
argument-hint: "Paste an arXiv/DOI/journal URL here"
---

# Paper Explainer Skill

Explain academic papers section-by-section in simple terms, with visual figures, background knowledge, equation walkthroughs, and a knowledge-graph narrative. **The full explanation is written to a self-contained HTML file** (Step 6); the chat shows only a minimal summary so the conversation stays readable.

---

## Output Routing (read first)

This skill produces two different things and they must not be confused:

| Surface | What appears there |
|---|---|
| **HTML export file** (the deliverable) | Everything from Steps 1–5 in full — Big Picture, all background subsections, knowledge graph, every section walkthrough, every equation, every diagram, every results table + chart, synthesis. This is the *only* place the full explanation lives. |
| **Chat** (minimal) | (1) A one-line status while fetching, (2) the Step 6 confirmation block with the file path, (3) a short TL;DR (3–5 bullets) so the user gets value without opening the file. **Nothing else.** |

**Hard rules:**
- **Do NOT print Steps 1–5 content to chat.** No Big Picture table, no background sections, no equations, no diagrams, no section walkthrough, no results tables, no synthesis bullets. Generate that content directly into the HTML file.
- **No inline SVG diagrams in chat.** Diagrams go into the HTML only.
- **No KaTeX/equation blocks in chat.** Equations go into the HTML only.
- **The chat output for a successful run is small** — typically under 20 lines total: status line → export confirmation → TL;DR.
- If the user asks a follow-up ("explain Section 3 in more detail", "go deeper on equation 4"), *that* answer goes in chat — follow-ups are conversational. The skill's silence rule applies only to the initial generation pass.

---

## Diagram & Table Rendering

All visuals are produced as **inline SVG** in the chat (and re-used verbatim in the HTML export). All tables are produced as Markdown tables in chat and as semantic `<table>` elements in the HTML export.

**Optional Visualizer tool:** if a Visualizer / diagram-rendering tool is available in the current environment (e.g., one exposing `read_me` with `{ module: 'diagram' }`), invoke `read_me` exactly once per response before the first diagram and prefer the Visualizer for SVG generation. If no such tool exists, **silently use inline SVG** — do not announce the fallback, do not emit fallback comments, do not call `read_me`.

---

## Step 0 — Fetch the Paper (with full fallback cascade)

**Hard rule:** Do not begin Step 1 until the **full body** of the paper (or the best obtainable substitute) has been successfully retrieved into context. No partial walkthroughs from just the abstract unless every fallback has failed and the user has been told.

### 0a. Identify the paper

Parse the input URL/identifier and extract every available ID:
- arXiv ID (e.g., `2005.11401`, with or without version suffix `v4`)
- DOI (e.g., `10.1038/s41586-023-12345-x`)
- ACL Anthology ID (e.g., `2020.acl-main.703`)
- PubMed ID / PMC ID
- Semantic Scholar paper ID (CorpusID)
- Paper title + first author (always derive these; needed for title-based search fallbacks)

### 0b. Fetch cascade — try sources in this order until one succeeds

For each candidate URL: `web_fetch` it, then verify success (non-empty body, contains recognizable section headings like "Abstract" / "Introduction" / "References", token count ≥ ~2000). If the response is a paywall page, a 404, a captcha, or a tiny stub, treat it as failed and continue.

**arXiv papers (`arXiv:XXXX.XXXXX`):**
1. `https://arxiv.org/html/XXXX.XXXXX` — ar5iv-style full HTML (richest, equations as MathML).
2. `https://arxiv.org/html/XXXX.XXXXX{vN}` — try the latest version suffix if base fails.
3. `https://ar5iv.labs.arxiv.org/html/XXXX.XXXXX` — community mirror with the same render.
4. `https://arxiv.org/pdf/XXXX.XXXXX` — fetch PDF and extract text.
5. `https://arxiv.org/pdf/XXXX.XXXXX.pdf` — alternate PDF URL pattern.
6. `https://www.arxiv-vanity.com/papers/XXXX.XXXXX/` — Vanity HTML render (may be offline; try anyway).
7. `https://arxiv.org/abs/XXXX.XXXXX` — abstract page (last resort for arXiv; flag as degraded).

**DOI papers:**
1. `https://doi.org/<DOI>` — follow redirects to publisher landing.
2. `https://www.semanticscholar.org/paper/<corpusID>` — Semantic Scholar mirror with extracted full text when available.
3. `https://api.semanticscholar.org/graph/v1/paper/DOI:<DOI>?fields=title,abstract,openAccessPdf,tldr` — fetch open-access PDF URL if present, then fetch that PDF.
4. `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC<id>/` — if a PMC ID exists, this is usually full-text open access.
5. `https://europepmc.org/article/MED/<PMID>` or `/PMC/<PMCID>` — Europe PMC mirror.
6. `https://www.researchgate.net/publication/<id>` — author-uploaded copy (often a PDF link).
7. Publisher landing page — extract abstract + any open sections.

**Title-based last-ditch search** (when ID-based routes all fail):
1. Search Semantic Scholar: `https://api.semanticscholar.org/graph/v1/paper/search?query=<URL-encoded title>&fields=title,authors,openAccessPdf,externalIds` — pick the top result whose title matches and fetch its `openAccessPdf.url` if present.
2. Search arXiv listing: `https://arxiv.org/find?query=<title>&searchtype=all` — pick matching result, restart cascade with its arXiv ID.
3. Search OpenReview: `https://openreview.net/search?query=<title>` — common for ICLR/NeurIPS/COLM papers.
4. Search Google Scholar via a public search tool if available; extract any PDF link from results and fetch.
5. Try `https://www.google.com/search?q=<title>+filetype:pdf` and fetch the first matching PDF link.

### 0c. PDF text extraction

When the only successful fetch is a PDF:
- Use whatever PDF-to-text capability is available (`web_fetch` on the PDF URL often returns extracted text directly; otherwise use a PDF reader tool).
- If extraction yields garbled output (ligatures, missing spaces, no section structure), retry with a different PDF source from the cascade before degrading.
- Preserve figure captions, equation labels, table rows. Lose nothing from the body.

### 0d. Verify completeness before proceeding

Before moving to Step 1, the agent must have all of:
- Title, authors, venue, year
- Abstract
- **All body sections** (Introduction through Conclusion)
- All numbered equations (or, if equations were lost to PDF extraction, the surrounding prose so they can be reconstructed)
- All figure captions and table contents
- Reference list (at minimum the inline citations needed for "Related Work" context)

If any of these are missing after the cascade exhausts, **tell the user explicitly** what is missing and from which source the partial content came, then ask whether to proceed with a degraded explanation or stop. Example:

> ⚠️ I could only retrieve the abstract + Introduction of this paper (the publisher landing was paywalled and no open-access PDF was found via DOI, Semantic Scholar, PMC, or title search). I can give you a high-level overview from those sections, but the Methods and Results walkthrough won't be possible. Continue, or do you have a PDF you can share?

### 0e. Re-use rule

If the paper is already fully in context from a previous turn in this conversation, **skip re-fetching**. Jump to the relevant step.

### 0f. Read the whole paper before generating

Once the full text is in context, **read through it end-to-end before producing any Step 1+ output.** Steps 1–5 must reflect the actual contents of the paper, not a guess from the title/abstract. If the model is tempted to start writing after only seeing the abstract, stop and re-read the body first.

### 0g. Output budget planning and multi-turn protocol (truncation prevention)

**The response token limit applies to everything generated in a single model response — including all tool call arguments.** Writing multiple `create_file` calls within one response does not bypass this limit; the combined size of all generated content still counts. The only reliable fix is **multi-turn generation where each turn writes one safe-sized chunk** — but turns must be as few as the content actually requires. Over-splitting wastes the user's time just as much as under-splitting causes truncation.

**Hard rules:**
- Never generate more content in a single turn than the per-turn budget allows.
- Never add turns beyond what the content genuinely needs. If everything fits in 2 turns, use 2 turns.
- Generation is **fully automatic** — no user input is needed between turns. Each turn immediately triggers the next without waiting.

#### 1. Measure the paper and compute a turn plan

After fetching the full paper text, compute these four metrics:

| Metric | How to estimate |
|---|---|
| **S** — section count | Count body sections (Abstract, Intro, … Conclusion; exclude references) |
| **E** — equation count | Count numbered/display equations in the paper |
| **F** — figure count | Count figures with captions |
| **W** — word count | Estimate from fetched token count × 0.75 |

Then assign each content block a **weight** (number of turn-slots it consumes):

| Block | Weight formula |
|---|---|
| HTML shell + Step 1 (Big Picture) | 1 turn-slot always |
| Step 2 — Background (2a–2e) | 1 turn-slot if E ≤ 4 and F ≤ 2; else 2 |
| Step 3 — each paper section | 1 turn-slot per section; merge adjacent short sections (< 400 words each) up to 3 per slot |
| Step 4 — Results | 1 turn-slot if ≤ 3 experiments; else 2 |
| Step 5 — Synthesis + Glossary + Footer | 1 turn-slot always |

**Total turns = sum of all weights.** This is the actual turn plan. No fixed minimum, no fixed maximum.

**Examples:**
- Short 8-page paper, 3 equations, 2 figures, 5 sections → shell(1) + bg(1) + sections merged into 2 slots + results(1) + synthesis(1) = **6 slots but sections merge to 2, so 6 total** — wait, let me give cleaner examples:
  - Short: shell(1) + bg(1) + 5 sections merged to 2 slots + results(1) + synthesis(1) = **6 turns** — that's still large. Actually:
  - *Tiny* 5-page abstract-only paper: shell+step1+step2 all fit in 1 slot (nothing complex), step3 in 1 slot, step4+step5 in 1 slot = **2–3 turns**.
  - *Typical* 12-page NeurIPS paper: shell(1) + bg(1) + 7 sections → 3 slots (3+2+2) + results(1) + synthesis(1) = **7 turns**.
  - *Long* 40-page paper with appendices: shell(1) + bg(2) + 15 sections → 5 slots + results(2) + synthesis(1) = **11 turns**.

#### 2. Per-turn content budget (hard caps)

These caps prevent any single turn from exceeding the response token limit:

- **Max HTML output per turn: ~25 KB of raw HTML text** (≈ 6,000 tokens of generated content, leaving headroom for the model's reasoning and tool call overhead).
- **Max paper sections per turn in Step 3:** 3 sections, or 1 section if it has > 600 words in the source.
- **Max SVG diagrams per turn:** 2.
- **Max KaTeX equation blocks per turn:** 4.
- **Max Chart.js charts per turn:** 2.

If the adaptive plan assigns content that would exceed any cap, split that slot into two.

#### 3. Scope controls (apply only if total turns would exceed 10)

Apply in order until turns ≤ 10:

1. **Trim Deep Dive callouts** — one-sentence summary; note `[expand in follow-up]`.
2. **Summarise appendix sections** — one paragraph per appendix.
3. **Collapse Background 2b–2d** — merge into a single condensed block.
4. **Abbreviate Related Work** — comparison table only, no prose.
5. **Reduce per-section diagrams** — one diagram per 3 sections instead of one per section.

Always note applied controls in the paper header: `<span class="scope-note">ℹ︎ [controls applied] — ask a follow-up to expand.</span>`

#### 4. Announce the plan (Turn 1 only, before any file writing)

Post a single status line to chat:

> *📄 [Paper title] — [N]-section [class] paper. Turn plan: [M] turns ([brief slot summary e.g. "shell · background · 3×sections · results · synthesis"]). Starting now…*

This is the only chat output until the final export confirmation. No per-turn status messages. No prompts asking the user to do anything.

#### 5. Automatic chaining — no user input required

**The skill executes all turns in sequence without pausing.** After writing each non-final turn's chunk to disk, the skill immediately proceeds to the next turn in the same agent loop. There is no `continue` prompt and no wait for user input.

Specifically:
- After Turn N's `create_file` or append call returns successfully, immediately begin generating Turn N+1 content.
- Do **not** post any intermediate chat message between turns.
- The **only** chat output is: (a) the Turn 1 plan announcement, and (b) the final export confirmation + TL;DR after the completeness check passes.
- If a turn's file-write call fails (tool error, disk full, etc.), post a single error line to chat and stop: `❌ Turn N failed: [error]. File is at [path] up to Turn N-1. Say "resume export" to retry from here.`

---

## Step 1 — Orient the Reader *(content goes into HTML, not chat)*

Give a **"Big Picture" orientation block** — written into the HTML export, not posted to chat:

1. **What field is this?** (e.g., machine learning, molecular biology, economics)
2. **What problem does it solve?** One sentence, plain English.
3. **Why does that problem matter?** Real-world stakes.
4. **What's the core idea/contribution?** The "aha" in one sentence.
5. **Who is the intended audience of the paper?** (helps calibrate depth)

---

## Step 2 — Background Knowledge Block *(HTML only)*

Identify the **prerequisite concepts** a reader needs. Structure in five layers:

### 2a. Core Prerequisites
For each concept the paper directly builds on:
- Plain-English definition (2–4 sentences)
- A concrete analogy or real-world example
- Key equation if relevant (see [Equation Style](./references/equations.md))
- Visual if it aids understanding (via Visualizer)

### 2b. Deeper Architecture/Domain Context
Go one level deeper than the paper itself:
- For ML papers: explain the model architecture (e.g., Transformer layers, attention heads, what Q/K/V actually *learn* to represent) not just the math.
- For biology papers: explain the biological system before the molecular mechanism.
- For systems papers: explain the hardware/software stack before the optimization.
- Use diagrams to show how the paper's contribution fits inside the larger system.

### 2c. Comparison Table: Prior Work
Produce an HTML comparison table contrasting this paper against 3–5 related prior methods. Columns: method name, key idea, complexity, limitations, what this paper fixes.

### 2d. Paper-Specific Concepts
Identify any concepts specific to this paper's domain — niche terminology, domain conventions, specific datasets or benchmarks. Define each briefly.

### 2e. Knowledge Graph Overview
Now that background is established, produce a **Knowledge Graph** — an inline SVG diagram showing the main concepts and how they connect. Use labelled nodes and arrows. Style: concept nodes in one color, relationship labels on edges, the paper's main contribution highlighted. This map is referenced throughout the walkthrough.

---

## Step 3 — Section-by-Section Walkthrough *(HTML only)*

Go through every section (Abstract → Introduction → Related Work → Methods → Experiments/Results → Discussion → Conclusion). For each section:

### Section Header Format
```
## [Section Name]
**What this section is doing:** [1-sentence purpose]
```

Rules:
- **No jargon without definition.** Every technical term gets a parenthetical plain-English gloss on first use.
- **Figures and diagrams:** For any figure referenced in the paper, reproduce the *concept* as an inline SVG. Draw a clean conceptual version, not an exact replica.
- **Equations:** Use the Equation Style in [./references/equations.md](./references/equations.md) for every non-trivial equation.
- **"Why does this matter?"** After each major claim or result, add a note on its significance.
- **Extra context:** Where the paper is terse, add background. Where it cites prior work, briefly explain what that work was.
- **Connections:** Use phrases like "Notice this connects back to [earlier concept]" to build the knowledge graph narrative.
- **Deep Dives:** Place `> 🔬 Deep Dive` callout blocks after any equation or claim whose proof/derivation is interesting but would interrupt the narrative.
- **Confidence tagging:** Any content drawn from your own background knowledge (not explicitly stated in the fetched paper) must be marked inline with a `ℹ︎ background` badge. This makes clear to the reader what is stated by the authors vs. added by the explainer.

---

## Step 4 — Results & Experiments *(HTML only)*

For each experiment or result:
- State what was being tested and why.
- Explain the metric(s) in plain English (e.g., "accuracy = what % of predictions were right").
- Summarize what the numbers show in one sentence.
- If there is a comparison table, produce a simplified version as an inline SVG bar chart or Markdown table.
- Call out the most important/surprising result explicitly.

---

## Step 5 — Synthesis & Knowledge Graph (Closing) *(HTML only)*

1. **What did we learn?** Bullet points, one per major contribution.
2. **What are the limitations?** (from the paper's Discussion + your own assessment)
3. **What comes next?** Likely future directions.
4. **Updated Knowledge Graph:** Redraw the Step 2e graph with all key concepts filled in — nodes for every concept introduced, edges labeled with relationships, the contribution clearly marked.

---

## Step 6 — Export (HTML, automatic) *(this is what chat sees)*

After the Step 1–5 content has been generated **into the HTML file** (not into chat), write the file to disk and post a minimal chat response.

Skip the auto-export **only** if the user explicitly said "don't export" / "no file" / "chat only" earlier in the same conversation — in that case, and only that case, post the full Step 1–5 content in chat instead.

### Chat response format (the only chat output for the initial run)

Post exactly these three things in chat, in order, and nothing else:

**1. Status line** (one line, posted *before* the export, while the paper is being fetched and content generated):

> *Fetching arXiv:2005.11401 … reading the full paper … generating HTML…*

**2. Export confirmation block:**

> **✅ Exported.**
> **File:** `rag-knowledge-intensive-nlp.html`
> **Location:** `C:\Users\t-aritradas\Downloads\`
> **Full path:** [`C:\Users\t-aritradas\Downloads\rag-knowledge-intensive-nlp.html`](file:///C:/Users/t-aritradas/Downloads/rag-knowledge-intensive-nlp.html)
> **Size:** 142 KB
> **Contents:** 12 sections · 7 equations · 3 diagrams · 2 interactive charts · 1 figure thumbnail
>
> Open it in any browser, or File → Print → Save as PDF for offline reading.
> *(Say "don't auto-export" next time to get the full explanation in chat instead.)*

**3. TL;DR** (3–5 bullets, plain text, no diagrams, no equations):

> **TL;DR**
> - *(paper's core problem in one line)*
> - *(the key idea / contribution in one line)*
> - *(the headline result in one line)*
> - *(main limitation or caveat in one line)*
> - *(who should care / what it unlocks in one line)*

That's it. **No section-by-section walkthrough in chat. No equations in chat. No SVG diagrams in chat.** All of that is in the HTML file.

Rules for the confirmation:
- **Always** show all four of: filename alone, parent directory alone, full absolute path, and file size in KB/MB.
- Format the full path as a clickable markdown link to the file (`[full-path](file:///C:/Users/.../file.html)`) so users in VS Code can open it with one click.
- If the write failed or fell back to a chat code block, use **❌ Export failed** or **⚠️ Wrote inline (no file tool available)** instead of ✅, and explain why. In the inline-fallback case, paste the HTML in a single fenced ```html code block after the confirmation and instruct the user to save it manually — this is the only case where chat shows large output.

**HTML is the only export format.** Markdown/PDF export is not produced. Direct the user to use the browser's Print → Save as PDF for offline PDF.

### Multi-turn writing protocol

Every paper uses multi-turn generation as defined in Step 0g. The rules for each turn:

**Turn 1 — always `create_file`:**  
Creates the file. Content: full `<head>` (CSS, font imports, CDN links), `<body>` open tag, paper header, ToC skeleton, Step 1. Ends with the body open and a `<!-- TURN 1 END -->` HTML comment so resume points are unambiguous.

**Turns 2–N-1 — always file append:**  
Each turn appends its assigned content to the existing file. Ends with a `<!-- TURN N END -->` comment. **Never re-creates the file.** If the file doesn't exist when an append is attempted (e.g., Turn 1 failed silently), recreate it from scratch and restart from Turn 1.

**Final turn — appends closing tags:**  
Appends Step 5 + Glossary + Footer + `</body></html>`. Does **not** add a turn comment after `</html>`.

**Turn isolation rule:** Each turn generates only the content for that turn — nothing from the next turn bleeds in. If a section runs long, stop at the section boundary and assign the overflow to the next turn.

**No user input between turns.** After each non-final turn's file-write succeeds, immediately begin the next turn without posting to chat or waiting. See Step 0g §5 for the automatic chaining rule.

**Handling `resume export` from the user:**  
When the user types `resume export` (triggered only after a write failure):
1. Re-read the current state of the file to find the last `<!-- TURN N END -->` comment.
2. Do **not** re-fetch the paper — it is already in context.
3. Resume from Turn N+1: append its content, then continue chaining automatically through all remaining turns.

### Completeness verification

After the final file-write call, **always verify the output is complete** before posting the export confirmation to chat. Run through this checklist in order:

#### Check 1 — File tail
Read the last 20 lines of the written file. The file **must** end with `</footer>` then `</body>` then `</html>` (ignoring whitespace). If any of these are missing, the response was truncated.

#### Check 2 — Required section anchors
Scan the file for the following `id` attributes. All must be present:

```
id="top"
id="step1" (or equivalent Big Picture section)
id="step2"
id="step3"
id="step4"
id="step5"
id="glossary"
```

#### Check 3 — HTML well-formedness sentinel
Count `<body` occurrences and `</body>` occurrences in the file. Both must equal exactly 1.

#### On failure — recovery protocol

If any check fails:

1. **Identify the last complete section** — read the file backwards to find the last properly-closed section (`</section>`) or the last complete chunk boundary.
2. **Resume from that point** — generate and append everything from the next section onward to the end of the file.
3. **Re-run all three checks** after the append.
4. Repeat up to **3 recovery attempts**. If the file still fails after 3 attempts, post a warning to chat:

> ⚠️ **Partial export.** The file at `[path]` is incomplete — the response budget was too tight for this paper. Completed sections: [list]. Missing: [list].
> Ask me to continue with `"continue export from [section name]"` and I will append the missing content.

5. Report in the export confirmation block whether recovery was needed, e.g.: `**Status:** Complete (1 recovery pass needed)`.

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

## Visual Design Principles

- Use CSS design tokens (never hardcode hex values).
- Knowledge graph nodes: rounded rectangles, gradient fill per type, drop-shadow.
- Equation diagrams: label each part with callout lines.
- Keep diagrams readable at ~840px width; scale gracefully to mobile (320px min).
- Interleave visuals with prose — do not cluster them all at the end.
- Only if a Visualizer tool is in use: set `loading_messages` (e.g., "Drawing the knowledge map…") and call `read_me` once before the first diagram. Otherwise emit the SVG directly with no announcement.

---

## Tone & Style

- Write as if explaining to a **curious, intelligent non-expert** — a grad student from a neighboring field, or a technically literate person encountering this area for the first time.
- Be enthusiastic about interesting ideas. It is OK to say "This is clever because…"
- Use analogies liberally. Compare math to cooking, algorithms to recipes, probability to weather forecasts.
- Vary sentence length. Short punchy sentences for key insights. Longer ones for nuance.
- Never say "as mentioned above" without specifying exactly what was mentioned.

---

## Follow-up Questions

When the user asks a follow-up about the same paper already in context:
- **Skip re-fetching.** The paper is already in context.
- Jump directly to the relevant section or step.
- For "go deeper on an equation" — load [./references/equations.md](./references/equations.md) and produce the full Deep Dive treatment.
- For "explain Section X again" — re-run Step 3 for that section only.
- For "export this" or "save this" — jump directly to Step 6.

---

## Edge Cases

See [./references/edge-cases.md](./references/edge-cases.md) for handling: math-heavy papers, empirical/ML papers, short/workshop papers, paywalled papers, very long papers, survey/review papers, systems/hardware papers, and multi-paper reading lists.

---

## Suggested Future Improvements

The following enhancements are **not yet implemented** but are strong candidates for the next version. Keep this list up to date when improvements are accepted or rejected.

| # | Improvement | Rationale | Effort |
|---|---|---|---|
| F-1 | **Interactive knowledge graph** — make nodes clickable; clicking a node scrolls to its first mention in the walkthrough. Implement with simple JS `addEventListener` on SVG `<g>` elements. | Dramatically improves navigability for long papers. | Low |
| F-2 | **Collapsible Deep Dive callouts** — wrap each `> 🔬 Deep Dive` block in a `<details><summary>` element, collapsed by default. | Keeps the main reading flow clean without losing depth. | Low |
| F-3 | **In-page search highlight** — a small `<input>` in the header that highlights matching terms across the document using the browser `mark` API. | Useful for long exports (50+ KB). | Medium |
| F-4 | **Reading time estimate** — compute `wordCount / 200` and display "~N min read" in the paper header. | Sets expectations for the reader. | Trivial |
| F-5 | **Copy-equation button** — a small clipboard icon next to each equation block that copies the raw LaTeX to clipboard. | Useful for researchers who want to reuse equations. | Low |
| F-6 | **Light/dark toggle button** — a moon/sun icon in the header that toggles a `.light` class on `<body>`, overriding `prefers-color-scheme`. | Some users open exports in bright rooms. | Low |
| F-7 | **Citation hover-cards** — inline citations `[Wei et al., 2022]` become `<abbr>` elements with a tooltip showing title + authors + year, derived from the reference list. | Eliminates need to scroll to references for common citations. | Medium |
| F-8 | **Section completion badges** — a faint checkmark badge on ToC entries as the user scrolls past each section (using `IntersectionObserver`). | Gives a sense of progress through a long document. | Low |
| F-9 | **Multi-paper comparison mode** — when the user pastes two or more paper URLs, produce a single HTML with a side-by-side comparison table and merged knowledge graph. | High value for literature review use cases. | High |
| F-10 | **Annotation layer** — a floating pencil icon that opens a sticky-note panel anchored to the nearest section; notes saved to `localStorage`. | Turns the export into an active reading tool. | High |

---

## Smoke Test

After any edit to this skill, run this one-liner to confirm the full pipeline still works:

> *"Explain arXiv:1706.03762 and export it."*

Expected behavior (verify each):
- Step 0 fetches the arXiv HTML version successfully.
- Step 2e produces a knowledge graph SVG with at least 5 nodes, using the gradient node fills and shared `<defs>` from the Diagram Design System.
- Step 3 walks every section with at least one equation rendered via KaTeX.
- Step 4 produces at least one results table **and** its Chart.js equivalent.
- Step 5 closes with an updated knowledge graph + limitations + future work.
- The reading progress bar appears and fills on scroll.
- The exported file uses Inter + JetBrains Mono fonts.
- CSS design tokens are defined in `:root`; no hardcoded hex values appear in `<style>`.
- Step 0g runs before any HTML is generated, computes S/E/F/W metrics, derives an adaptive turn plan, and announces it in a single chat status line.
- The turn count matches actual content weight — a short 5-page paper does **not** use more turns than necessary; a 30-page paper does **not** try to fit into 2 turns.
- No `continue` prompt is posted. All turns execute automatically in sequence with no user input.
- Turn 1 uses `create_file`; all subsequent turns use append. Each non-final turn ends with a `<!-- TURN N END -->` comment.
- No single turn exceeds: ~25 KB HTML output, 3 paper sections, 2 SVG diagrams, 4 equations, 2 charts.
- The response token limit error does **not** appear on any turn.
- The only chat outputs are: (a) the Turn 1 plan announcement, (b) the final export confirmation + TL;DR.
- Completeness Check 1 (file ends with `</html>`), Check 2 (all required `id` anchors present), and Check 3 (single `<body>`/`</body>` pair) all pass after the final turn.
- For arXiv:1706.03762 ("Attention Is All You Need", ~15 pages): verify the adaptive plan produces a reasonable turn count (expected ~5–6) and no turn is over-budget.
- Step 6 writes `~/Downloads/attention-is-all-you-need.html` (or similar slug) and posts a chat summary listing counts (sections, equations, diagrams, charts, figure thumbnails).
- Opening the file in a browser: math renders, charts render, back-to-top appears on scroll, glossary tooltips fire on hover, `<noscript>` banner is hidden, footer shows skill version + timestamp.

If any expected item is missing, the skill regressed — check recent edits to the corresponding step.
