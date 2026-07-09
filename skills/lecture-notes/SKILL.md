---
name: lecture-notes
description: "Use when a user shares a YouTube (or similar) lecture video or playlist URL from a university/research source (Stanford, MIT, CMU, Berkeley, DeepMind, Harvard, etc.) and wants study notes, detailed notes, a breakdown, or a summary to learn from. Also triggers on: 'make notes from this lecture', 'notes for this course/playlist', 'summarize this lecture to learn it', 'explain this lecture video', 'turn this talk into notes'. Trigger on a bare lecture/playlist URL that looks educational. Do NOT use for entertainment videos, news, music, or non-educational clips, and do NOT use for papers (use paper-explainer for arXiv/DOI)."
argument-hint: "Paste a lecture or playlist URL (Stanford/MIT/etc.)"
---

# Lecture Notes Skill

Turn university / research **lecture videos** into **self-contained, visual, learn-by-understanding
HTML study notes** — one file per video, plus an `index.html` hub for playlists. Notes are
print-to-PDF ready and follow a fixed, evidence-based design and pedagogy.

**Domain-agnostic:** works for ML, physics, CS, math, biology, economics, law, etc. The
*structure and pedagogy are fixed*; the *content and examples adapt* to the lecture's subject.

---

## Output Routing (read first)

| Surface | What appears there |
|---|---|
| **HTML note files** (the deliverable) | The full notes — sections, diagrams, equations, worked example, trace, checks, glossary, references. This is the only place the full content lives. |
| **Chat** (minimal) | (1) short status while fetching, (2) playlist-scope question if needed, (3) final confirmation with file paths + a 3–5 line TL;DR + the recommended reading order. Nothing else. |

**Hard rules:** don't dump full note prose, diagrams, or equations into chat — write them into
the HTML. Chat for a successful run is small. Follow-up questions ("go deeper on section 3")
are answered conversationally in chat.

---

## Reference files (load as needed)
- **Styling & rendering:** [`./references/styling.md`](./references/styling.md) — the locked
  theme, fonts rationale, Mermaid/MathJax/SVG rules, print CSS. **Read before authoring.**
- **Pedagogy:** [`./references/pedagogy.md`](./references/pedagogy.md) — the note-authoring
  loop, required elements, tone, anti-patterns.
- **Enrichment:** [`./references/enrichment.md`](./references/enrichment.md) — how to build the
  always-on Prerequisites refresher, Worked numeric example, and End-to-end trace per domain.
- **Edge cases:** [`./references/edge-cases.md`](./references/edge-cases.md) — no captions,
  non-English, very long, playlists, whiteboard math, paywalled, panels, etc.

## Assets
- **Template:** [`./assets/note-template.html`](./assets/note-template.html) — copy its
  `<head>` verbatim; fill the body placeholders. `./assets/index-template.html` for the hub.
- **Transcript fetcher:** [`./assets/fetch_transcript.py`](./assets/fetch_transcript.py).
- **Validator:** [`./assets/validate.js`](./assets/validate.js).

---

## Step 0 — Acquire the transcript

**Hard rule:** do not author a note until that video's transcript is in context.

### 0a. Parse the URL
Detect **single video** vs **playlist** (`list=` param). Extract video id(s).

### 0b. Playlist → confirm scope FIRST
If a playlist, enumerate it and **ask the user** how much to cover before any bulk work:
```
python <skill>/assets/fetch_transcript.py list "<playlist_url>"
```
Offer: a foundational batch (~5), the whole course, a specific version/module, or a
hand-picked set. Then order the chosen set **pedagogically** (overview → mechanics →
applications), not just by playlist index. See `edge-cases.md`.

### 0c. Fetch + clean each chosen video
```
python <skill>/assets/fetch_transcript.py get "<video_url_or_id>" "<workdir>/transcripts"
```
This installs `yt-dlp` if missing, downloads the cleanest English captions (manual → auto),
de-duplicates the VTT, and writes `<id>.txt` (prints `{id, txt, words}` as JSON). If it reports
no captions, follow `edge-cases.md`.

### 0d. Read the whole transcript before authoring
Read end-to-end. Identify **domain, level, the lecture's real arc, its worked examples,
equations, and every paper/person/book it names.** Auto-captions are messy — use them for
*emphasis and order*, rely on correct domain knowledge for facts/spelling (cross-check names).

---

## Step 1 — Plan the note (per video)

Draft the section outline from the *actual lecture arc*, then map on the fixed scaffolding
(see `pedagogy.md`): hook (WHY) · running analogy · **Prerequisites 30-sec refresher** ·
numbered sections→subsections with ≥1 diagram and key equations · **Worked numeric
micro-example** · **End-to-end trace** · check-yourself prompts · recap-as-questions ·
glossary · references. Pick the one running analogy now. Decide the domain-appropriate form of
the worked example and the trace (see `enrichment.md`).

## Step 2 — Author the HTML note

1. Copy `assets/note-template.html`'s entire `<head>` **verbatim**; set only `<title>`.
2. Fill the body: replace every `{{PLACEHOLDER}}`, following `pedagogy.md` + `enrichment.md`.
3. Diagrams: Mermaid in `<figure><div class="mermaid">…</div></figure>` (**always close the
   `</div>`**, quote special labels). Hand-author an inline SVG for the one "money" schematic.
   Equations: MathJax `\(…\)` / `$$…$$`, every symbol interpreted. See `styling.md`.
4. One file per video: `notes/<video_id>.html`. Wire prev/next + `index.html` in `.navbtns`.

**Budget:** authoring is token-heavy. If a note (or a batch) would exceed a single response,
generate across multiple automatic turns — one safe-sized note (or file) per turn — never
truncate mid-file. For playlists, generate in batches and validate each batch.

## Step 3 — Build the index hub (playlists / multi-note)

From `assets/index-template.html`: a learning-path hub with one card per note in reading
order, a "how to use these notes" box, and a "what each note contains" list. `index.html`
lives **in the same folder as the notes**, so its links are same-folder (`<id>.html`, not
`notes/<id>.html`).

## Step 4 — Validate the render (don't assume)

```
# one-time, per machine (bundled Chromium download is often blocked):
cd <workdir> ; npm init -y ; $env:PUPPETEER_SKIP_DOWNLOAD="true" ; npm install puppeteer
# then (NODE_PATH lets the skill's validate.js find puppeteer installed in <workdir>):
$env:NODE_PATH="<workdir>\node_modules" ; node <skill>/assets/validate.js notes/<id1>.html notes/<id2>.html ...
```
It drives a system Edge/Chrome (auto-detected; override with `$env:BROWSER_PATH`) and asserts
every Mermaid diagram rendered (`svgs == blocks`, no "Syntax error") and MathJax produced
output, with no JS errors. **Fix and re-run until every file prints `[PASS]`.** The usual
failure is an unclosed `</div>` in a figure or an unquoted Mermaid label. If no browser is
available, follow the manual-audit fallback in `edge-cases.md`.

## Step 5 — Deliver (chat, minimal)

Report: file paths (and the `index.html` to open first), a 3–5 line TL;DR of what the
lecture/batch covered, and the recommended reading order. Offer the next batch for playlists.

---

## Follow-ups
- "add an interactive / a code snippet / more examples to note X" → open that file, add the
  element (see the optional list in `enrichment.md`), re-validate.
- "restyle all notes" → use a single transform script that swaps the whole `<style>` block
  across every file, then re-validate all (see `styling.md`). Never hand-edit N files apart.
- "continue the playlist" → next pedagogical batch, same template, extend the index + nav.

## Smoke test (self-check before declaring done)
- [ ] Each note copies the template `<head>` verbatim (fonts + MathJax + Mermaid + `<style>`);
      only `<title>` differs. No hardcoded hex outside `:root`.
- [ ] Every note has: hook, running analogy, **prereq box**, ≥1 diagram, key equation(s),
      **worked numeric example**, **end-to-end trace**, ≥4 checks, recap-as-questions,
      glossary, references.
- [ ] All Mermaid `<div class="mermaid">` are closed before `</figure>`; special labels quoted.
- [ ] `validate.js` prints `[PASS]` for every file (or manual audit done + stated).
- [ ] `index.html` in the notes folder; same-folder links; prev/next wired across notes.
- [ ] Chat output is minimal (paths + TL;DR + reading order).
