# Styling & Rendering Rules (lecture-notes)

The look is **locked**: a dark "notebook" page with **light *paper* cards** for diagrams, an
ultra-legible body font, and a distinctive handwritten font for headings. Do not invent new
palettes — copy `assets/note-template.html`'s `<head>` (fonts + MathJax + Mermaid + `<style>`)
**verbatim** into every note, changing only the `<title>`.

## Why this exact setup (evidence-based)
- **Body → Atkinson Hyperlegible.** Engineered for character disambiguation → lowers
  *extraneous* cognitive load (Cognitive Load Theory, Sweller) so working memory goes to
  understanding, not decoding. This is what sustains attention on dense material.
- **Headings + callout labels → Caveat (handwritten).** Distinctive markers exploit the
  **von Restorff / isolation effect** (distinctive items are better recalled) and speed
  section navigation — *without* taxing body reading.
- **Do NOT** chase "hard fonts aid memory" (Sans Forgetica / disfluency): the effect largely
  failed replication and hurts long-form study.
- **Dark page + light paper cards for figures.** Guarantees hand-authored inline SVGs (which
  use light fills + dark strokes) stay visible, and reads like sketches pinned to a notebook.

## Design tokens (already in the template `:root`)
Dark page `--bg:#14161b`, ink `--ink:#e9e6dc`, paper card `--paper:#f7f2e6`. Accents:
`--accent` blue, `--accent2` purple. Callout variants: `why / intuition / analogy / check /
pitfall / eqn / prereq`. **Never hardcode hex outside `:root` in new CSS** — reuse tokens.

## Equations — MathJax (CDN)
- Inline: `\( ... \)`  ·  Display: `$$ ... $$` or `\[ ... \]`.
- Interpret every symbol the moment it appears. Prefer a displayed equation inside a
  `.box.eqn` for the "key equation" of a section.

## Diagrams — Mermaid (CDN, `theme:'neutral'`)
- Every diagram: `<figure><div class="mermaid"> ... </div></figure>` — **ALWAYS close the
  `</div>` before `</figure>`** (the single most common breakage).
- **Quote any node label** containing spaces-with-special-chars, parentheses, `:`… and write
  line breaks as `<br/>` inside quotes: `A["softmax(QKᵀ/√d)<br/>weights"]`.
- Good diagram types: `flowchart`, `sequenceDiagram`, `timeline`, `stateDiagram-v2`,
  `classDiagram`, `graph`. Keep ≤ ~12 nodes; one idea per figure; add a `<figcaption>`.
- Neutral (light) theme is intentional so diagrams sit on the light paper card.

## Hand-authored inline SVG (for the "money" diagram)
- Put it in a `.svgcard` (or directly inside a `<figure>`). Use light fills (#eef…, #fff) with
  dark strokes/text (#1b1f24, #2f6df6) — it renders on the light paper card.
- Use for schematics Mermaid can't do well (e.g., a pipeline with math annotations, a grid
  being split into patches, a matrix). Keep it clean (Tufte: no non-informative ink).

## Print / PDF
The template already ships a `@media print` block that flips to a clean light layout (so
MathJax `currentColor` math and text stay readable on white). **Do not remove it.** Users
export via Ctrl/Cmd-P → Save as PDF.

## Self-contained rule
Each note is ONE standalone `.html`. CSS is embedded; only MathJax, Mermaid, and Google Fonts
load from CDN (so rendering needs internet — state this in the footer/README). Do not add a
build step or external CSS/JS files.

## Multi-file consistency (playlists)
All notes in a run share the identical `<head>`. If you later restyle, use a transform script
that replaces the whole `<style>…</style>` block across every file at once, then re-validate —
never hand-edit N files divergently.
