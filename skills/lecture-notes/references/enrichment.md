# Enrichment Elements (lecture-notes)

Three enrichments are **always-on** in every note. They are what turn a transcript summary
into something that builds real understanding. Each generalizes across domains — the *form*
is fixed, the *content* adapts to the subject.

---

## #7 — Prerequisites: 30-second refresher  (`.box.prereq`, placed right after the hook)

**Purpose:** diagnose and close gaps *before* the learner hits them, lowering cognitive load.

**Form:** a short bulleted list. Each bullet = **one bold concept** + a one-line reminder +
*why it's needed in this note*. Keep to the handful that actually matter for this lecture. If
a prerequisite is itself deep, link to another note or a canonical explainer instead of
teaching it here.

**Domain examples**
- ML/DL: "**Dot product** — measures alignment of two vectors; here it scores query–key
  similarity." · "**Softmax** — turns scores into a probability distribution that sums to 1."
- Physics: "**Conservation of energy** — total energy is constant in a closed system; we use
  it to shortcut the dynamics below." · "**Partial derivative** — rate of change holding
  other variables fixed."
- Algorithms: "**Big-O** — how runtime grows with input size; we compare it before/after."
- Biology: "**Central dogma** — DNA → RNA → protein; the pathway below is a special case."

---

## #2 — Worked numeric micro-example  (its own `<h2>` section)

**Purpose:** concrete-before-abstract. Numbers make the core mechanic click and expose exactly
what each operation does.

**Form:** pick the **smallest honest instance** of the section's central mechanic and compute
it *by hand*, showing **every intermediate value**, ending in the result. Use `$$…$$`. Follow
with a `details.check` that asks the reader to redo the last step with one input changed.

**Rules:** use tiny, round numbers (2–3 elements, integers or simple decimals). Show the
arithmetic, don't just state the answer. If the mechanic isn't numeric, use the smallest
concrete *symbolic* instance instead.

**Domain examples**
- ML: a 3-token self-attention with 2-D Q/K/V vectors → show \(QK^\top\), the scaling, the
  softmax digits, and the weighted-sum output.
- Physics: plug real numbers into the derived formula (e.g., a projectile with \(v_0=10,\
  \theta=30^\circ\)) and carry units through.
- Algorithms: trace the recurrence/DP table for an input of size 4, cell by cell.
- Statistics: compute the estimator on 5 data points, showing each term.

---

## #4 — End-to-end trace: follow one concrete instance  (its own `<h2>` section)

**Purpose:** the "where am I in the pipeline?" map. Learners lose the thread across many
stages; a single traced instance with the **state at each step** fixes this. Best rendered as
a `<table>` with a `Step | What happens | State/shape/value` layout (the `.tt` class styles
the state column).

**Form:** choose ONE concrete input and walk it through the *whole* process, one row per stage,
tracking the quantity that changes. End with a `.box.intuition` naming the structural insight
the trace makes obvious.

**Generalization of "state" per domain**
- ML/DL: **tensor shapes** (and sometimes values) — e.g., `image (224×224×3) → patches
  (196×768) → +CLS (197×768) → encoder (197×768) → head → logits (1000)`.
- Physics: the evolving **state variables** (position, momentum, field value) step by step.
- Algorithms: the **data-structure state** after each iteration (the array/stack/tree).
- Systems/networking: a **packet/request** traced through each layer/component.
- Biology/chem: **one molecule/signal** followed through each step of the pathway/reaction.

---

## Optional (offer, don't force)
If the user asks for more, the next-best additions are: a runnable code snippet, an
interactive HTML explorable (vanilla-JS widget with a "predict before you drag" prompt),
misconception callouts beyond the required one, scale anchors (concrete real-world numbers),
and a from-scratch derivation box. Keep these opt-in to avoid bloat.
