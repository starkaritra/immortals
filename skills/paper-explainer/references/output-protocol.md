# Paper Explainer — output budget & multi-turn protocol

> Reference for the `paper-explainer` skill. Load when planning a long/multi-turn
> generation to avoid truncation. Core workflow lives in `../SKILL.md`.

### 0g. Output budget planning and multi-turn protocol (truncation prevention)

**The response token limit applies to everything generated in a single model response — including all tool call arguments.** Writing multiple `create_file` calls within one response does not bypass this limit; the combined size of all generated content still counts. The only reliable fix is **multi-turn generation where each turn writes one safe-sized chunk** — but turns must be as few as the content actually requires. Over-splitting wastes the user's time just as much as under-splitting causes truncation.

**Hard rules:**
- Never generate more content in a single turn than the per-turn budget allows.
- Never add turns beyond what the content genuinely needs. If everything fits in 2 turns, use 2 turns.
- Generation is **fully automatic** — no user input is needed between turns. Each turn immediately triggers the next without waiting.

#### 1. Measure the paper and compute a turn plan

After fetching the full paper text, compute these four metrics:

| Metric | How to estimate |
|---|---|
| **S** — section count | Count body sections (Abstract, Intro, … Conclusion; exclude references) |
| **E** — equation count | Count numbered/display equations in the paper |
| **F** — figure count | Count figures with captions |
| **W** — word count | Estimate from fetched token count × 0.75 |

Then assign each content block a **weight** (number of turn-slots it consumes):

| Block | Weight formula |
|---|---|
| HTML shell + Step 1 (Big Picture) | 1 turn-slot always |
| Step 2 — Background (2a–2e) | 1 turn-slot if E ≤ 4 and F ≤ 2; else 2 |
| Step 3 — each paper section | 1 turn-slot per section; merge adjacent short sections (< 400 words each) up to 3 per slot |
| Step 4 — Results | 1 turn-slot if ≤ 3 experiments; else 2 |
| Step 5 — Synthesis + Glossary + Footer | 1 turn-slot always |

**Total turns = sum of all weights.** This is the actual turn plan. No fixed minimum, no fixed maximum.

**Examples:**
- Short 8-page paper, 3 equations, 2 figures, 5 sections → shell(1) + bg(1) + sections merged into 2 slots + results(1) + synthesis(1) = **6 slots but sections merge to 2, so 6 total** — wait, let me give cleaner examples:
  - Short: shell(1) + bg(1) + 5 sections merged to 2 slots + results(1) + synthesis(1) = **6 turns** — that's still large. Actually:
  - *Tiny* 5-page abstract-only paper: shell+step1+step2 all fit in 1 slot (nothing complex), step3 in 1 slot, step4+step5 in 1 slot = **2–3 turns**.
  - *Typical* 12-page NeurIPS paper: shell(1) + bg(1) + 7 sections → 3 slots (3+2+2) + results(1) + synthesis(1) = **7 turns**.
  - *Long* 40-page paper with appendices: shell(1) + bg(2) + 15 sections → 5 slots + results(2) + synthesis(1) = **11 turns**.

#### 2. Per-turn content budget (hard caps)

These caps prevent any single turn from exceeding the response token limit:

- **Max HTML output per turn: ~25 KB of raw HTML text** (≈ 6,000 tokens of generated content, leaving headroom for the model's reasoning and tool call overhead).
- **Max paper sections per turn in Step 3:** 3 sections, or 1 section if it has > 600 words in the source.
- **Max SVG diagrams per turn:** 2.
- **Max KaTeX equation blocks per turn:** 4.
- **Max Chart.js charts per turn:** 2.

If the adaptive plan assigns content that would exceed any cap, split that slot into two.

#### 3. Scope controls (apply only if total turns would exceed 10)

Apply in order until turns ≤ 10:

1. **Trim Deep Dive callouts** — one-sentence summary; note `[expand in follow-up]`.
2. **Summarise appendix sections** — one paragraph per appendix.
3. **Collapse Background 2b–2d** — merge into a single condensed block.
4. **Abbreviate Related Work** — comparison table only, no prose.
5. **Reduce per-section diagrams** — one diagram per 3 sections instead of one per section.

Always note applied controls in the paper header: `<span class="scope-note">ℹ︎ [controls applied] — ask a follow-up to expand.</span>`

#### 4. Announce the plan (Turn 1 only, before any file writing)

Post a single status line to chat:

> *📄 [Paper title] — [N]-section [class] paper. Turn plan: [M] turns ([brief slot summary e.g. "shell · background · 3×sections · results · synthesis"]). Starting now…*

This is the only chat output until the final export confirmation. No per-turn status messages. No prompts asking the user to do anything.

#### 5. Automatic chaining — no user input required

**The skill executes all turns in sequence without pausing.** After writing each non-final turn's chunk to disk, the skill immediately proceeds to the next turn in the same agent loop. There is no `continue` prompt and no wait for user input.

Specifically:
- After Turn N's `create_file` or append call returns successfully, immediately begin generating Turn N+1 content.
- Do **not** post any intermediate chat message between turns.
- The **only** chat output is: (a) the Turn 1 plan announcement, and (b) the final export confirmation + TL;DR after the completeness check passes.
- If a turn's file-write call fails (tool error, disk full, etc.), post a single error line to chat and stop: `❌ Turn N failed: [error]. File is at [path] up to Turn N-1. Say "resume export" to retry from here.`

---
