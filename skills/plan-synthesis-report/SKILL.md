---
name: plan-synthesis-report
description: >
  managerAS-family skill for synthesizing the results of a multi-agent plan into a single
  bottom-line-up-front report for the user. Triggers on: "summarize what the agents did",
  "give me the final report", "wrap up this plan", "synthesize the results", "bottom line",
  "executive summary of the run". Owns the durable craft of leading with the answer, tracing
  each result to the agent/artifact that produced it, surfacing residual risk and
  uncertainty honestly, and stating the recommended next action. Use at the end of an
  orchestrated run. Do NOT use it to plan or route — that's managerAS's planning phase.
argument-hint: "Point me at the run's artifacts/event log (or paste the per-agent outputs) and the original mission"
---

# plan-synthesis-report Skill

Close a multi-agent run the way a good CEO briefs: the answer first, then the evidence, then
what's still uncertain and what to do next.

## When to use
- A `plan/v1` DAG has finished and its per-node artifacts need to become one human answer.
- The user asks for a wrap-up, executive summary, or "so what did we get?".

## Principles (managerAS JARVIS + CEO layers)
1. **Bottom-line up front (BLUF).** First sentence = the result / recommendation. The user
   should get the answer without reading further.
2. **Trace to source.** Every claim maps to the agent + artifact id that produced it — no
   unattributed assertions. Reference artifacts by id, don't inline-dump them.
3. **Radically honest about uncertainty.** State confidence, what's assumed, what failed or
   was skipped, and what a reader should distrust. Never imply more certainty than the run
   earned.
4. **Surface by exception.** Lead with what matters; push routine detail into an appendix the
   user can expand.
5. **End with a decision.** A recommended next action (or a crisp choice with a default),
   never a shrug.

## Report structure
```
<Mission restated in one line>

BOTTOM LINE: <the answer/recommendation in 1–2 sentences>

What we did:
  • <agent> → <artifact id>: <one-line result>
  • …
Key findings:
  1. <finding> — evidence: <artifact id / metric>
  2. …
Residual risk / uncertainty:
  • <open assumption, failure, or low-confidence area> — impact.
Recommended next step: <action, or choice + default>

Appendix (on request): full artifact index, metrics, provenance.
```

## Method
1. **Fold the run.** Read the event log / artifact set; reconstruct what each node produced
   and whether it succeeded (validated seam contracts).
2. **Extract the through-line.** Tie the artifacts back to the original mission's success
   criteria — did we meet them?
3. **Weigh confidence.** Note nodes that failed, were re-planned, or produced low-confidence
   output; reflect that in the residual-risk section.
4. **Write BLUF-first**, plain language (managerAS voice: calm, concise, honest, lightly
   dry — never hype).

## Guardrails
- No claim without an artifact behind it.
- Don't bury a failure — a partial or failed run must say so up front.
- Keep it skimmable: the user reads the first three lines and knows where they stand.

## Handoff
This is managerAS's **synthesis phase** output. Planning/routing/execution happen before it;
this skill only turns finished artifacts into the user-facing brief.
