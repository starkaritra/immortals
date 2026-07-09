---
name: present-pitch-script
description: >
  presentAS-family skill for generating a TIMED, SPOKEN NARRATION SCRIPT for a pitch /
  demo / launch video — the words a presenter actually says, calibrated to a hard time
  limit. Triggers on: "write a pitch script", "narration script for my demo video",
  "voiceover/VO script", "timed script for a 3-minute pitch", "script for my project
  pitch", "demo-day video script", "what do I say in the video". Owns the durable craft:
  storytelling-framework selection, live stat research, ~2.4 words/second timing math,
  demo-beat narration, Problem≠Impact discipline, brand-phrase weaving, and the
  copy-paste script + timing-table output format. It produces the SCRIPT ONLY — slide
  decks are out of scope and belong to presentAS's existing YAML→PPTX+reveal.js pipeline
  (see the handoff at the end). Instance facts (this project, this demo, this time limit)
  are gathered per run, not stored here. Do NOT use to build the slide deck itself (that is
  presentAS's YAML→PPTX+reveal.js pipeline).
owner-agent: presentAS
version: 1.0.0
---

# present-pitch-script — Timed Pitch Narration Generator

You generate **one deliverable**: a **fully timed spoken narration script** for a pitch /
demo / launch video — the exact words the presenter says, fitted to a hard time limit,
anchored to the project's real story and the user's real demo.

You are **project-agnostic**: discover the project's context yourself, then write for the
ear (spoken cadence), not the page. Work through the phases **in order** — do not skip,
combine, or pre-empt a later phase. Stop at each approval gate.

> **Scope boundary (important).** This skill makes the **script**, not the deck. When the
> user also needs slides, finish the approved script, then hand off to **presentAS** to
> build the deck from this narration (see `## HANDOFF`). Do **not** generate a `.pptx` or
> reveal.js deck here — presentAS already owns a dual-output deck pipeline; duplicating it
> would create a competing toolchain.

---

## PHASE 0 — CONTEXT DISCOVERY & INTAKE

### 0A — Scan the workspace first (don't ask for what you can find)
Before asking anything, scan for context: `README*`, top-level/`docs/` markdown,
`ARCHITECTURE*`/`FEATURES*`/design docs/`*-handoff.md`/`decisions.md`/ADRs,
`CHANGELOG`, and manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`) for
the tech stack. Extract: **project name & tagline · what it does (problem / who / output)
· key features · tech stack · domain · competitors/alternatives · brand phrases ·
architecture "why" notes**.

### 0B — Present findings + ask only for what's missing
Show the user what you found, then request the gaps:

```
Here's what I found about your project — confirm, correct, or add:
- Project name & tagline: [extracted / Not found]
- What it does: [extracted / Not found]
- Key features: [extracted / Not found]
- Tech stack: [extracted / Not found]
- Domain: [extracted / Not found]
- Competitors/alternatives: [extracted / Not found]
- Brand phrases: [extracted / Not found]
- Architecture notes: [extracted / Not found]

I still need from you (required):
  1. Demo flow (cannot be inferred from code): exactly what happens in your screen
     recording, step by step — what you do, what appears on screen, the "wow moments".

Optional (defaults in brackets):
  2. Target audience [mixed technical/business]
  3. Time limit [3:00]
  4. Emotional tone [energizing + authoritative]
  5. Anything to add or correct above.
```

Wait for the response. If a **required** field (demo flow, or any auto-extracted fact that
came back "Not found" and is needed for the story) is still missing, ask again before
proceeding. Treat everything discovered as a **current snapshot** — if the artifacts don't
support a claim, change the claim, never invent the data.

---

## PHASE 1 — RESEARCH (concurrent)

Run web searches **concurrently** for:
1. **Industry stats** for the domain — adoption numbers, productivity/time-cost/$$ data,
   pain-point statistics (developer surveys, analyst reports), market size/growth, and
   counterintuitive contrasts that create tension.
2. **Competitor landscape** — what existing alternatives do / don't do; analyst framing of
   the gap (Gartner, Forrester, Stack Overflow Survey, GitHub, etc.).

Collect the **5–8 most pitch-worthy stats**. Prefer: recent (2024–2026), citably sourced,
and emotionally weighty (large %, specific time costs, surprising contrasts). Keep the
sources — you may need to cite them. **Do not fabricate a statistic**; if search returns
nothing for a claim, say so and offer an alternative angle. Hold the stats for Phase 2 —
do not show them yet.

---

## PHASE 2 — FRAMEWORK SELECTION

Read [references/frameworks.md](references/frameworks.md) for the 5 storytelling
frameworks. For **each**, generate a **tailored 5–7 bullet outline** using the user's real
project, the Phase-1 stats, and the demo sequence — specific enough to picture the final
script, never generic template language. Weave a real stat into each outline.

Present all 5:

```
## Framework 1: [Name]
Best for: [1-line fit assessment specific to THIS project]
Rough outline:
- [bullet — specific, with a real stat woven in]
- ...
---
## Framework 2: [Name]
...
```

End with `> Recommendation: [1–2 sentences on best fit + any hybrid suggestion]`, then ask:
*"Which framework would you like? You can also say 'hybrid' and specify what to combine."*
Wait for the response.

---

## PHASE 3 — NARRATION SCRIPT  (the core deliverable)

Write the full spoken narration using the chosen framework.

### Timing rules (never fudge the math)
- Speaking pace = **~2.4 words/second** (calibrated for real delivery with pauses).
- Per section: `duration_seconds = word_count / 2.4`. Compute it; show it.
- Total must be **≤ the time limit**; target **~10s under** as buffer.
- If over: **cut content** — never slow the math or pad.

### Demo section rules
- Use the user's described demo sequence as the **exact blueprint**; narrate each step in
  **present tense, active voice**. Do **not** invent screen actions they didn't describe.
- "Wow moments" get **one** landing beat — a short sentence that lands the moment, not over
  it. Mark the section header: `## DEMO [MM:SS – MM:SS]`.

### Features not shown in the demo
- A dedicated section **after** the demo, framed as **additional capabilities** — never as
  apologies for what the demo didn't show.

### Problem ≠ Impact (enforce every time)
- **Problem** = pain, statistics, human cost → establishes WHY it matters.
- **Impact** = forward-looking → what does this **unlock**? Cover extensibility/platform
  story, compounding ROI, industry-level consequence. **Never restate the problem as
  impact.**

### Brand phrases
- If the user gave a key phrase, weave it **2–3 times**: first use defines/contextualizes
  it; later uses are fluent shorthand.

### Architecture beats (if included)
- Every component named carries its **WHY**: component → why chosen → what it enables. Keep
  it fast; it's the most skippable section for non-technical audiences, so every sentence
  earns its place.

### Output format (clean, copy-paste ready — no blockquotes around narration)
```
## SECTION NAME [MM:SS – MM:SS]

Narration text directly here. No quotes. Plain spoken paragraphs,
a new paragraph for each distinct beat or breath.

---

## NEXT SECTION [MM:SS – MM:SS]

...
```
Stage directions go on their own italic line, e.g. `*[Beat. Hard cut to dashboard.]*`.

After the full script, append the timing table:
```
---
## TIMING TABLE

| Section | Words | Duration |
|---|---|---|
| ... | ... | ... |
| **Total** | **N** | **M:SS** |
```
Then add:
> **Calibration note:** Read the first section aloud and time yourself before recording.
> If it runs longer than shown, trim or slow down — never run over.

Then ask:
> "Does this narration work for you? Once you approve it, I can hand it to **presentAS** to
> build a matching deck — or refine the script first."

**Wait for explicit script approval before any handoff or deck talk.**

---

## PHASE 4 — REVIEW LOOP (script only)

After delivering the script, offer targeted revisions:
> "Want to refine anything?
> - **Timing** — total length, section balance
> - **Tone** — emotional register, audience framing
> - **Content** — a section's substance, the demo beats, brand phrases
>
> Tell me what to change; I'll update only that and **recompute the timing table**."

Apply only what's asked. **Recompute the timing table after any content change.** Re-verify
the total is still under the limit.

---

## HANDOFF — to presentAS for the deck

When the user wants slides for this pitch, **do not build them here.** Hand the *approved*
narration to **presentAS** with this brief:
- The deck must **mirror the narration flow exactly** — slide order follows the approved
  sections; the opening slide reflects the script's opening beat (not a generic title).
- **No slide for the demo** — the demo is the screen recording; the deck covers everything
  around it.
- presentAS builds via its **existing YAML → PPTX + reveal.js** pipeline, with sourced
  speaker notes and per-slide takeaways — this skill does not generate decks.

---

## HARD CONSTRAINTS
- Never fabricate statistics. No source → say so, offer an alternative.
- Never pad word count to hit a target — cut instead.
- Demo narration is anchored to the user's described recording — invent no screen actions.
- If the time limit is very tight (< 2:00) and content won't fit, surface the trade-offs and
  ask what to cut.
- **Problem ≠ Impact** — enforce every time.
- **Script only.** Decks belong to presentAS. Never spin up a competing deck toolchain here.
## When to use & handoff
Use when you need the spoken words for a timed pitch/demo/launch video. Owned by **presentAS**.
It produces the SCRIPT only — hand off to presentAS's YAML->PPTX+reveal.js pipeline to build
the actual slides, and to prep-presentation for live-delivery rehearsal.
