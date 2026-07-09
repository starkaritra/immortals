# Pedagogy Rules (lecture-notes)

The deliverable is **understanding**, not coverage. A note passes only if a learner could
rebuild the idea from first principles, explain it simply, and apply it somewhere new. These
rules are domain-agnostic — they hold for an ML lecture, a physics lecture, or a law lecture.

## The note-authoring loop (per lecture)
1. **Read the whole transcript first.** Identify the *domain*, the *level* (intro vs advanced),
   the lecture's *actual arc*, its worked examples, equations, and any papers/books/people it
   cites. Notes must reflect what the lecture actually taught, not a generic summary.
2. **Motivate WHY before HOW.** Open every note (and ideally every major section) with the
   problem the concept solves or the question it answers — *before* any definition.
3. **One concrete example before the general rule.** Never state the abstract rule first.
   Specific case → the pattern → *then* name it (definitions are endpoints, not openers).
4. **Pick one running analogy and commit to it** across the whole note. Don't swap metaphors.
5. **Chunk into sections/subsections**; one or two ideas per chunk. Tie every symbol/term to a
   concrete meaning the moment it appears.
6. **Signal epistemic status** where relevant: is this a *definition*, a *derived result*, or
   an *analogy/speculation*? (Especially for research talks that mix fact and conjecture.)
7. **Check by production, not recognition.** Never write "does that make sense?". Use
   `details.check` prompts that make the reader *predict / apply / compute*, with the answer
   hidden until they expand (generation effect + retrieval practice).
8. **Name the misconception, then dismantle it** (`.box.pitfall`) — "most people picture X;
   here's where it breaks."
9. **Close with recap-as-questions** (not a summary) + a **teach-it-back** prompt.

## Required elements in every note
- Hero (title, presenter, source link, duration) + one-line WHAT & WHY (`.lead`).
- `.box.why` hook + `.box.analogy` running analogy.
- **Prerequisites 30-sec refresher** (`.box.prereq`) — see `enrichment.md`.
- Numbered sections → subsections following the lecture; ≥1 diagram; key equations in `.box.eqn`.
- **Worked numeric micro-example** + **end-to-end trace** — see `enrichment.md`.
- ≥ ~4 "✓ Check yourself" prompts spread through.
- Recap-as-questions, Glossary table, References (sources named + best follow-ups).

## Adapt depth to the lecture
- **Intro lecture** → assume little; more analogies, more worked examples, gentler pace.
- **Advanced/research talk** → assume the basics; spend the depth on the novel contribution,
  the intuition behind results, and honest limitations; keep the prereq box tight but real.
- **Match the lecturer's own examples** where they're good — the learner will hear them again
  in the video, so reusing them reinforces rather than competes.

## Tone
Warm, patient, precise. Never "simply / obviously / trivially / just". Normalize genuine
difficulty. Short, gated chunks over walls of text. The learner is capable; the material is
hard; your job is to lower the friction.

## Anti-patterns (never)
Definition-first openings · jargon before grounding · answer-before-attempt · skipping the
check · walls of text · fake-Socratic theater · passive re-exposition instead of retrieval.
