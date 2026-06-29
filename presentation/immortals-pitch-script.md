# Immortals — Microsoft Demo-Day Pitch (Voice-Over Script)

**Format:** recorded pitch video · **Audience:** everyone at Microsoft (PM · Applied/DS · SWE)
**Target length:** ~5:00 · **Pace:** ~2.4 words/sec · **Word count:** ~702 (≈ 4:52, ~8s under)
**Arc:** Problem → Aggravate → Solution → How it works → Trial run (demo) → Results → Vision

> Read at a calm, confident pace (~2.4 w/s). Pause one beat at each `—`. The `## DEMO`
> block is the screen recording; everything else is spoken over the slides. The deck
> (`immortals-pitch.html`) mirrors these sections one-to-one. **No slide for the demo
> itself** — the demo *is* the recording described in the DEMO block.

---

## [00:00 – 00:33]  PROBLEM — the hook
You have more good ideas than you will ever ship. A research dive you keep postponing.
A tool you would build if you had a free week. A paper, a prototype, a plan — all stuck
in the same place: your head. Not because the idea is weak — but because *doing* it means
becoming a researcher, a critic, an engineer, and a project manager, all at once.
So the idea waits. And most of them quietly die there.

## [00:33 – 00:59]  AGGRAVATE — and the tools don't help
And the AI tools meant to help? They hand you a wall of text and walk away. You are still
the one who has to break the work down, check it, fix it, and stitch it together. One
chatbot. One generalist. No plan, and no memory of what it did an hour ago. You did not
get a team — you got another tab to manage.

## [00:59 – 01:35]  SOLUTION — what Immortals is
Immortals is different. It is **an enterprise team you delegate to**. You hand one manager
your goal, in plain English — and it **brings your ideas to life**. The manager writes a
real plan, picks the right specialists — a researcher, a critic, a coder, an experimenter —
and runs them for you. You talk to one agent; a whole expert team does the work behind it.
You delegate the task. You get back a finished result.

## [01:35 – 02:30]  HOW IT WORKS — the technical core, simply
Here is how, simply. The manager turns your goal into a **typed plan** — a DAG, a flowchart
of tasks with the right order built in. A **deterministic orchestrator** runs that plan: it
routes each step to the right specialist, and checks every hand-off against a contract — so
each output is valid input for the next. **Guardrails** cap time and cost, and risky steps
wait for your **approval**. Every move lands in an append-only **event log** — so the whole
run is auditable and replayable. The creative parts stay creative;
the coordination stays deterministic, auditable code.

## DEMO [02:30 – 03:38]  TRIAL RUN — the screen recording (present tense)
Let's watch it work. This is the Immortals bubble. I type one sentence — *"build me a weekly
digest of new AI research."* Instantly it assembles a team — you can see the plan as a small
flowchart: research, then critique, then build. Then it goes quiet and works. **Silence is the
default** — no firehose of pings. A live counter shows the routine decisions it is handling on
its own. It interrupts me exactly once — for a genuine judgment call — and notes that it held
back nine routine choices to ask this one. I answer, and it finishes: a verified report,
stamped with who did what. Now — a hard cut to the dashboard. Because this is not a mockup.
Here is a *real* run: the actual plan, the event timeline, the cost. Fully auditable.

## [03:38 – 04:30]  RESULTS — the proof
And that real run delivered. We gave Immortals a genuine build — a weekly research digest:
a Cloudflare backend plus a Chrome extension, end to end. Four steps, three specialists, real
agents. It passed **all eight** of our pre-registered success criteria. The code it shipped:
**seventy-eight of seventy-eight tests passing**, type-clean. But here is the moment that
matters. The critic agent — on its own — caught a critical flaw the first plan missed:
summarizing one item at a time would blow a hard platform limit and abort the whole digest.
The coder fixed it with batching. The team produced *better* architecture than the plan it was
handed. Honest caveat: the agents build and test headlessly — the final deploy is still a human
click. But that is not one yes-man chatbot. That is a real, critical team.

## [04:30 – 05:00]  VISION — the close
This is real today, at minutes-scale. The vision is bigger: a long-running agent you delegate
to for days — that survives restarts, learns which calls you want to make, and **earns**
more autonomy as it does. Always task-scoped; never watching your life. Microsoft's
mission is to empower every person and organization to achieve more. Immortals gives every one
of us an expert team to delegate to — so your next idea doesn't wait in your head. It ships.

---

## Timing table

| # | Section | In–Out | Words | Est. @2.4 w/s | Slide |
|---|---|---|---|---|---|
| 1 | Problem (hook) | 00:00–00:33 | 79 | 33s | 1 — "Your best ideas are stuck in your head" |
| 2 | Aggravate | 00:33–00:59 | 62 | 26s | 2 — "AI gave you a chatbot, not a team" |
| 3 | Solution | 00:59–01:35 | 84 | 35s | 3 — "An enterprise team you delegate to" |
| 4 | How it works | 01:35–02:30 | 110 | 46s | 4 — "Plan → orchestrate → verify (DAG)" |
| 5 | **DEMO** (recording) | 02:30–03:38 | 137 | 57s | 5 — "What you just saw / the loop" |
| 6 | Results | 03:38–04:30 | 134 | 56s | 6 — "8/8 · 78/78 · the catch" |
| 7 | Vision / close | 04:30–05:00 | 92 | 38s | 7 — "Delegate for days · 8 — Close" |
| — | **Total** | **~04:52** | **~702** | **~292s** | 8 slides |

> Buffer to the 5:00 ceiling: ~9 seconds. If a take runs long, trim Section 4 first
> (drop "and replays exactly") then Section 6 (drop the platform-limit clause). Never cut
> the Socrates catch — it is the heart of Results.

## Brand phrases (woven, as required)
- **"an enterprise team you delegate to"** — defined in §3, the through-line.
- **"brings your ideas to life"** — §3.
- **"silence is the default"** — §5 (the demo), the proactivity differentiator.

## External stats
None added. The script relies entirely on Immortals' own measured numbers (8/8, 78/78,
4 nodes / 3 specialists, the Socrates catch) — no third-party statistics were introduced,
so nothing here needs an external citation. (Hook is rhetorical, not a stat.)

## Per-section sources (one fact → one source)
- §3–§4 mechanism (manager → typed plan/DAG → deterministic orchestrator → seam-contract
  validation → guardrails/approval → event log → replay): `README.md`;
  `design/handoff.md` AS-029; `immortals/contracts/schemas/` (`plan/v1`, `artifact/v1`,
  `event/v1`).
- §5 demo loop (bubble: delegate → team-as-DAG → silent work + routine-decision counter →
  one calibrated ping + "held back N" → verified provenance report; dashboard: real run, DAG,
  timeline, cost): `prototype/jarvis-bubble/index.html` + `README.md`;
  `immortals/dashboard/` (`immortals dashboard`, README "dashboard" section).
- §6 results (4 nodes / 3 specialists; 8/8 pre-registered criteria; 78/78 tests = worker 55 +
  extension 23; 155,540 output tokens; ~42 min; 22-event log; Socrates caught the Cloudflare
  50-subrequest/invocation flaw → Linus batched summarization; headless = build/typecheck/
  tests/dry-run, deploy manual): `design/evidence/agentsuite-empirical-validation-2026-06-20.md`.
- §7 vision (long-running days-scale, durable/survives restarts, earned autonomy, task-scoped
  not life-watching; roadmap Phases 6.5–10): `design/handoff.md` AS-029; `design/plan.md`
  Phases 6.5–10. Microsoft mission: official Microsoft mission statement.
