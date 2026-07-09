# references/specs.md — Poster size & spec resolution

Where to look for the **authoritative** physical spec, and what to capture. Always prefer
the venue's own page for the *exact edition*; never rely on memory or a previous year.

## Where to find the official spec (in priority order)
1. **Venue site, this edition**: pages titled *Call for Posters*, *Poster Instructions*,
   *Presentation Guidelines*, *Author Guide*, *Camera-Ready & Poster*, *FAQ for Presenters*.
   Search: `"<venue> <year>" poster size instructions`, `"<venue> <year>" "poster" cm OR inches`.
2. **The acceptance email / OpenReview author console** — many venues put the size there.
3. **The poster-printing vendor the venue partners with** (often lists exact board size).
4. **Last edition's instructions** — use only as a hint, and say it's unconfirmed for this year.
5. **If still unresolved → ask the user in writing.** Never guess a print size.

## What to capture (the spec table)
| Field | Why it matters |
|---|---|
| **Orientation** | portrait vs landscape drives the entire layout; some venues mandate one. |
| **Max dimensions + units** | the hard print size; mm vs inches matters — convert and show both. |
| **Board / easel size** | if the board is bigger/smaller than the poster, margins change. |
| **Mounting** | push-pins / Velcro / adhesive / clips → affects edge margins & where not to print. |
| **On-site printing** | some venues print for you with a required file format/aspect. |
| **Digital / virtual poster** | hybrid venues want a digital file (often 16:9 or a set ratio + PDF). |
| **Poster number / header zone** | some venues reserve a corner for an assigned number. |

## Common default sizes (offer these when asking the user)
| Name | Dimensions | Notes |
|---|---|---|
| **A0 portrait** | 841 × 1189 mm (33.1 × 46.8 in) | Most common worldwide. |
| **A0 landscape** | 1189 × 841 mm | Common for wide result grids / systems diagrams. |
| **A1** | 594 × 841 mm | Smaller boards, some workshops. |
| **US 48 × 36 in (landscape)** | 1219 × 914 mm | Common at US venues. |
| **US 36 × 48 in (portrait)** | 914 × 1219 mm | Common at US venues. |
| **Custom** | per CFP | Always defer to the CFP over any default. |

## Unit hygiene
- Convert and state both metric and imperial (1 in = 25.4 mm).
- For LaTeX `beamerposter`, size is set via `\usepackage[size=a0,orientation=portrait,scale=…]`
  or a custom `\geometry{paperwidth=…,paperheight=…}` — match the spec exactly.
- For PPTX, set slide width/height in inches or cm (PowerPoint caps a slide at 56 in /
  142.24 cm per side — for larger posters design at **half scale** and print at 200%).
- For HTML, set CSS `@page { size: <W> <H>; }` and design at real units (mm/in) or a 1:1 px map.

## Readability budget (sanity-check against the spec)
- Title legible from ~3–5 m; body legible from ~1.5–2 m.
- Rule of thumb min font sizes at A0: **title ≥ 72–96 pt, section heads 36–48 pt,
  body 24–32 pt, captions ≥ 20 pt.** Scale proportionally for other sizes.
- A reader spends ~3 minutes. If body text won't be readable at the spec size, cut content
  — do not shrink below the budget.
