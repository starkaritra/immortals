# Immortals — JARVIS bubble (concept mockup)

A **standalone, scripted** prototype of what Immortals feels like as a desktop assistant: a
floating bubble you delegate a task to, that works **silently** and pings you **once** — only
when it genuinely needs a call you must make — then hands back a verified, provenance-stamped
deliverable.

> **This is a mockup, not the product.** It is pure HTML/CSS/JS with canned data and fake timed
> animations — **not** wired to the orchestrator or any live run. It exists to demonstrate the
> intended experience (the AS-029 north star) before the Phase 7–10 backend exists.

## Run it
Open `index.html` in any browser. No build, no server, no dependencies.

## What it shows
A persona toggle — **PM · Applied/DS · SWE** — each playing the same loop with a role-tailored
task, so the value lands for anyone at Microsoft:

1. **Delegate** — you hand it a task in plain English.
2. **Team forms** — it routes to named specialists (researchAS, discussAS, coderAS, …) as a
   deterministic **DAG plan**, not one chatbot.
3. **Works silently** — collapses to a calm "working" pill; a live counter of **routine
   decisions it handled itself** (silence is the default).
4. **One ping** — a single, genuinely interrupt-worthy check-in (a judgment fork it must not
   decide for you), with a *why-I'm-asking* justification and a **"I held back N routine
   choices"** anti-spam proof.
5. **Finished report** — the tangible deliverable, **full provenance** (who did what + evidence),
   **verification** chips, and "auditable — reconstructable from the event log."

It auto-plays hands-off (the ping auto-resolves if left alone), or you can click a ping option
and hit **Replay** / switch personas.

## Strengths it dramatizes (the real Immortals differentiators)
- A **routed multi-agent specialist team** + a deterministic plan/DAG — not a single generalist.
- **Calibrated proactivity**: pings only when it must; everything else handled silently.
- A **verified, provenance-stamped** outcome — a finished deliverable, not a chat reply.
- **Auditability** — every step reconstructable from the event log.

See `design/handoff.md` (AS-029) and `design/plan.md` (Phases 6.5–10) for how the real thing is
built behind this experience.
