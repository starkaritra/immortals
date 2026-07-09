---
name: interactive-explorable
description: >
  teachAS-family skill for building self-contained interactive HTML explorables — the
  3Blue1Brown / Bret Victor style "play with the idea" widgets that make a concept tangible.
  Triggers on: "make an interactive visualization", "build a simulation of", "let me play
  with this concept", "an explorable for", "animate how X works", "interactive demo of".
  Owns the durable craft of turning one concept into a single-file HTML page with live
  controls, an honest model, and clear intuition-building. Use when a learner needs to
  manipulate a concept, not just read it. Do NOT use it for production app UI (that's
  frontend work).
argument-hint: "Name the concept and the one variable/relationship you want the learner to feel"
owner-agent: teachAS
version: 1.0.0
---

# interactive-explorable Skill

Build a single-file, dependency-light HTML widget that lets a learner *manipulate* a concept
and see the consequence — intuition before formalism.

## When to use
- A concept is best understood by playing with a parameter (eigenvalues, gradient descent,
  Fourier series, probability, a physics system).
- teachAS wants to hand the learner something runnable, not just an explanation.

## Design principles
1. **One idea, one knob (mostly).** Center the widget on the single relationship you want
   felt. Add secondary controls only if they deepen that one idea.
2. **Direct manipulation.** Sliders/drag/click that update the visualization *live* (Bret
   Victor: the learner changes something and immediately sees the effect).
3. **Honest model.** The simulation must reflect the real math/physics — no faked curves.
   If you approximate, say so on-screen.
4. **Intuition scaffolding.** Short caption that motivates *why* the idea matters, a
   "try this" prompt, and a visible readout of the key quantity as the user explores.
5. **Progressive disclosure.** Start simple; reveal complexity (formula, edge cases) behind
   a toggle so it doesn't overwhelm.

## Build spec
- **Single `.html` file**, self-contained: inline `<style>` and `<script>`. No build step.
- **Zero required network deps.** Prefer vanilla JS + `<canvas>` or SVG. If a library truly
  helps (e.g. a plotting lib), pin it via CDN and degrade gracefully.
- **Responsive & keyboard-accessible** controls; readable at presentation size.
- **Reset button** and sensible defaults so the learner can always get back to a known state.
- Render math with MathJax/KaTeX (CDN) only if formulas are shown.

## Output
- One `<concept>.html` the learner opens directly in a browser.
- A one-paragraph teaching note: what to notice, what to try, and the "aha".

## Quality check before shipping
- Does moving the control produce the *correct* change (verify against the real math)?
- Does it load and run offline from a file:// path?
- Would a novice grasp the idea in <60s of play?

## Handoff
**teachAS** owns the pedagogy (diagnosis, sequencing, checks-for-understanding); this skill
produces the explorable artifact it embeds in a lesson. For static talk visuals, hand to
**presentAS**; to verify a complex widget works, use the **webapp-testing** skill.
