---
name: latex-build
description: >
  paperAS/paper-poster-family skill for compiling LaTeX sources to PDF reliably and reading
  the errors when it fails. Triggers on: "build my paper", "compile this .tex", "make a PDF
  from LaTeX", "my LaTeX won't compile", "fix this build error", "run bibtex/biber",
  "beamerposter build". Owns the durable craft of choosing the right engine
  (pdflatex/xelatex/lualatex), running the full bib pass, parsing the log for the true first
  error, and producing a clean PDF. Use whenever a .tex/.bib artifact needs to become a PDF
  or a build is failing. Do NOT use it to write paper content — that stays with paperAS.
argument-hint: "Point me at the main .tex file (and its dir); tell me the engine if you have a preference"
owner-agent: paperAS
version: 1.0.0
---

# latex-build Skill

Compile LaTeX to PDF deterministically, and when it breaks, find the *real* error fast.

## When to use
- A `.tex`/`.bib` source needs to be turned into a PDF (paper, poster, CV, slides).
- A LaTeX build is failing and the log needs triage.
- Bibliography/citations aren't resolving.

## Engine selection
| Use engine | When |
|---|---|
| `pdflatex` | Default; ASCII/Latin text, standard packages, fastest. |
| `xelatex` / `lualatex` | System/OpenType fonts (`fontspec`), Unicode, `beamerposter` with custom fonts, CJK. |

Pick `xelatex` if the source loads `fontspec`/`unicode-math` or references `.ttf`/`.otf`.

## Standard build recipe (full bibliography pass)
Run from the source directory. The classic sequence resolves refs, citations, and cross-refs:

```
<engine> -interaction=nonstopmode -halt-on-error <main>.tex
bibtex <main>        # or:  biber <main>   (if the doc uses biblatex+biber)
<engine> -interaction=nonstopmode -halt-on-error <main>.tex
<engine> -interaction=nonstopmode -halt-on-error <main>.tex
```

- Use **`biber`** when the preamble has `\usepackage[backend=biber]{biblatex}`; otherwise
  **`bibtex`**.
- `latexmk -pdf` (or `-xelatex`/`-lualatex`) does all passes automatically — prefer it when
  available: `latexmk -pdf -interaction=nonstopmode -halt-on-error <main>.tex`.

## Reading a failed build
1. Open `<main>.log`. Search for the **first** line starting with `!` — that is the true
   error; everything after is fallout.
2. Common causes and fixes:
   - `! Undefined control sequence` → missing `\usepackage{...}` or a typo'd macro.
   - `! LaTeX Error: File 'X.sty' not found` → install the package (TeX Live: `tlmgr install X`).
   - `! Package biblatex Error: ... backend=biber` → run `biber`, not `bibtex` (or vice-versa).
   - `Citation 'foo' undefined` / `Reference ... undefined` → re-run the bib pass + 2 more
     `<engine>` passes.
   - Font errors under `pdflatex` → switch to `xelatex`/`lualatex`.
3. Report the first error line + file:line + the one-line fix. Re-run and confirm a PDF was
   produced (`<main>.pdf` exists and page count > 0).

## Environment check (before building)
- Verify a TeX distribution exists: `pdflatex --version` (or `xelatex`/`latexmk`).
- If none, tell the owner and suggest TeX Live / MiKTeX rather than guessing.

## Guardrails
- **Don't invent packages or fixes.** Read the actual `.log` error; propose the specific
  package/change it points to — never guess-install a chain of packages.
- **Never claim success without a PDF.** Verify `<main>.pdf` exists and has pages > 0.
- **Don't silently switch engines** mid-build without saying why (e.g., pdflatex→xelatex for
  fonts) — report the reason.
- **Treat `\input`/`\write18` shell-escape with care** — never run a build with `-shell-escape`
  on untrusted `.tex` without flagging it.

## Handoff
This skill produces the **PDF**. Content authorship, structure, and venue strategy remain
with **paperAS**; poster layout/spec remains with the **paper-poster** skill (which calls
this skill for its final beamerposter build).
