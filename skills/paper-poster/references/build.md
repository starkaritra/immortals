# references/build.md — Build scaffolds & toolchains per format

Copy-pasteable starting points and the commands to render + verify each format. Always set
the **exact spec size** from Phase 1 and **verify the rendered page size** after building.

---

## 1. LaTeX / beamerposter → PDF (default)

### Scaffold (A0 portrait shown; change `size`/`orientation` or use custom geometry)
```latex
\documentclass[final]{beamer}
\usepackage[size=a0,orientation=portrait,scale=1.3]{beamerposter} % match the CFP exactly
% For a non-standard size, instead use:
%   \usepackage[orientation=portrait,scale=1.3]{beamerposter}
%   \geometry{paperwidth=914mm,paperheight=1219mm} % e.g. US 36x48 in
\usetheme{default}
\usepackage{graphicx,booktabs,tikz,qrcode}
\usepackage[T1]{fontenc}

\title{\huge PAPER TITLE}
\author{Authors}
\institute{Affiliations}

\begin{document}
\begin{frame}{}
  % --- Title bar: title, authors, affils, logo slot, QR ---
  % \includegraphics[height=...]{institution-logo.pdf}
  % \qrcode[height=...]{https://project-or-paper-url}

  \begin{columns}[t]
    \begin{column}{.32\textwidth}
      \begin{block}{Motivation}  ... \end{block}
      \begin{block}{Method}
        % \includegraphics[width=\linewidth]{method.pdf} % FIGURE slot
      \end{block}
    \end{column}
    \begin{column}{.34\textwidth}
      \begin{block}{}\centering \Huge THE ONE FINDING \end{block}
      \begin{block}{Results}
        % \includegraphics[width=\linewidth]{results.pdf} % FIGURE slot
      \end{block}
    \end{column}
    \begin{column}{.32\textwidth}
      \begin{block}{Takeaway} ... \end{block}
      \begin{block}{References \& Contact} ... \end{block}
    \end{column}
  \end{columns}
\end{frame}
\end{document}
```
Themes worth offering: stock `beamerposter` blocks, or community themes **tikzposter**,
**baposter**, **gemini** (clean modern, popular at ML venues), or **betterposter** template.
Pick to match the Phase-2 venue history.

### Build + verify
```powershell
latexmk -pdf poster.tex      # or: pdflatex poster.tex (run twice for refs)
# verify page size (PowerShell, if pdfinfo available):
pdfinfo poster.pdf | Select-String "Page size"
```
- If no TeX toolchain: write the `.tex` + the one-line build command and tell the user to run it.
- Check: page size == spec; no missing-figure errors; note any overfull `\hbox`.

---

## 2. PowerPoint single-slide (python-pptx)

```python
from pptx import Presentation
from pptx.util import Inches, Pt
prs = Presentation()
# Set EXACT spec size. PPT caps a side at 56 in; for larger, design at half and print 200%.
prs.slide_width  = Inches(36)   # poster width
prs.slide_height = Inches(48)   # poster height
slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
# one text box / picture per content block:
tb = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(34), Inches(4))
tb.text_frame.text = "PAPER TITLE"
tb.text_frame.paragraphs[0].font.size = Pt(96)
# slide.shapes.add_picture("method.png", Inches(1), Inches(6), width=Inches(11))
prs.save("poster.pptx")
print(prs.slide_width, prs.slide_height)  # verify EMUs (914400 EMU = 1 in)
```
- Install if needed: `pip install python-pptx`.
- Verify: `slide_width/914400` and `slide_height/914400` (inches) == spec.

---

## 3. HTML / CSS (single self-contained page, print-to-PDF at spec)

```html
<!doctype html><html><head><meta charset="utf-8"><style>
  @page { size: 841mm 1189mm; margin: 0; }   /* A0 portrait — match the CFP */
  html,body { margin:0; width:841mm; height:1189mm; font-family:'Source Sans 3',Arial,sans-serif; }
  .poster { display:grid; grid-template-columns:1fr 1fr 1fr; gap:30mm; padding:40mm; }
  .title { grid-column:1/-1; font-size:96pt; font-weight:800; }
  .finding { font-size:64pt; font-weight:700; text-align:center; }
  .block h2 { font-size:40pt; } .block p,li { font-size:28pt; }
</style></head><body>
  <div class="poster">
    <div class="title">PAPER TITLE — authors — affils <img src="qr.png" style="height:80mm;float:right"></div>
    <div class="block">Motivation / Method …</div>
    <div class="finding">THE ONE FINDING</div>
    <div class="block">Results / Takeaway / Refs …</div>
  </div>
</body></html>
```
- Render to PDF at exact size via a headless browser if available
  (`chrome --headless --print-to-pdf=poster.pdf --no-pdf-header-footer poster.html`) or
  tell the user to "Print → Save as PDF" with the page size set.
- Verify the produced PDF page size == spec.

---

## QR code generation (offline, $0)
```python
import qrcode
qrcode.make("https://project-or-paper-url").save("qr.png")   # pip install qrcode[pil]
```
Place per the chosen layout (title bar or lower corner). Never call a paid QR service.

---

## Figure handling
- Pull figures from the paper's source (the `.tex`/`figures/` dir, or export pages from the
  PDF). Prefer **vector** (PDF/SVG/EPS) so they scale to poster size without pixelation;
  raster must be ≥ 150 dpi at final printed dimensions.
- Where a figure isn't available, leave a clearly-labeled placeholder box
  (`[FIGURE: method overview — drop in Fig. 2]`) and list it in the final checklist so the
  user knows exactly what to add.

## Final verification checklist (every build)
- [ ] Rendered page size == the confirmed spec (show the measured value).
- [ ] Every `[FIGURE]`/`[TABLE]` slot is filled or flagged.
- [ ] Fonts meet the readability budget (`references/specs.md`).
- [ ] QR resolves to the right URL.
- [ ] File opens; report absolute path + measured dimensions.
