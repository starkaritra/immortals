---
name: prep-interview
description: >
  prepAS family playbook for preparing high-stakes INTERVIEWS — job/PPO/return-offer
  interviews, internship conversions, Applied-Scientist / ML / data-science / SWE loops,
  and any "interview me / mock me / prep me for my interview" request. Triggers on:
  "prep me for my interview", "PPO interview", "return offer", "mock interview me",
  "Applied Scientist interview", "ML/DS/SWE interview", "behavioral round prep",
  "system design interview", "what will they ask me". Holds the durable question-space
  taxonomy, coverage categories, answer frameworks (STAR+L, metric-selection, system
  design), pitfalls, and model patterns that transfer across every interview. Instance
  facts (this company, this date, this project) live in the per-scenario tracker, not here.
---

# prep-interview — family playbook

An interview tests four things at once: **can you do the work** (skills), **have you done it**
(your project/experience), **will we want to work with you** (behavioral/values), and **how do
you think** (first-principles reasoning under probing). Cover all four. The single biggest
differentiator at senior/AS level is not knowing answers — it's **defending reasoning from
first principles** and **being honest about limits**.

## Coverage map (MECE categories — weight by the role's actual split)
Score each cell Probability×Impact×(5−Readiness); work top-priority first.
1. **Project / experience depth** — your own work, defended to the nittiest detail.
2. **Role-specific fundamentals** — the first-principles core of the discipline.
3. **Scenario / applied judgment** — "what would you do in this case", open-ended.
4. **System design** — structured design of a realistic system (ML or software).
5. **Coding / problem-solving** — DSA / implementation, think-aloud.
6. **Behavioral / values** — STAR+L stories mapped to the company's stated values.
7. **The anchors** — "tell me about yourself", "why this company/role", "your questions".

## The two failure modes to pre-empt
- **Knowing WHAT but not WHY.** For every fact about your project, pre-write the *why*: why
  this design, what you rejected, what the tradeoff was. Interviewers probe one level past
  recall. "Why not X?" is the real question behind every "what did you do?"
- **Over-claiming.** Naming a limitation honestly beats a fabricated number. Senior
  interviewers are *listening* for over-claiming. "I haven't validated that yet, here's how I
  would" is a strong answer, not a weak one.

## Project deep-dive prep (own-work mastery)
For each major component and decision, prepare the **decision quartet**:
1. **What** you did (one crisp sentence).
2. **Why** that approach (the first-principles justification).
3. **What you rejected** and why (shows you considered the space).
4. **The tradeoff / what's still imperfect** (shows judgment + honesty).
Then anticipate the **"how would you make it 10× / handle failure / scale it"** follow-up for
each. Re-read your own code/design docs so the detail is *exact*, not approximate.

## Metric-selection scenario framework (the "what metric would you use?" weapon)
A signature Applied-Scientist question. NEVER answer with a bare metric. Use this skeleton:
1. **Clarify the objective & the decision** the metric drives. "What action does this number
   trigger?" A metric exists to support a decision.
2. **Name the cost asymmetry.** What's worse — a false positive or a false negative? That
   choice picks precision-vs-recall emphasis.
3. **Propose a primary metric + guardrails.** One metric to optimize, 1–2 guardrails so you
   don't win on paper and lose in reality (e.g. quality up, latency/cost not worse).
4. **State assumptions & failure modes.** Class imbalance → PR-AUC over ROC-AUC; need a real
   probability → calibration (ECE/Brier), not just ranking; offline proxy → must validate online.
5. **Say how you'd validate** the metric itself (does it correlate with the outcome you care about?).
Worked classics to have ready: precision/recall/F1, ROC-AUC vs PR-AUC, calibration (ECE,
Brier, reliability diagram), regression (MAE/RMSE/MAPE), ranking (NDCG/MRR/MAP), LLM-eval
(human eval, LLM-as-judge + its biases, inter-annotator agreement / Cohen's-Fleiss kappa),
A/B (lift + CI, guardrails), classification under imbalance.

## ML / DS fundamentals to have cold (first-principles, not memorized)
Bias-variance tradeoff · overfitting & the regularization toolkit (L1/L2, dropout, early
stopping, data) · train/val/test & cross-validation & leakage · the metric zoo above ·
class imbalance (resampling, class weights, threshold-moving, PR-AUC) · calibration ·
evaluation design (offline vs online, proxy vs true objective) · feature/data leakage ·
the bias-variance reason behind every "why is my model bad" answer · for LLM/eval roles:
hallucination & grounding, offline vs online eval, LLM-as-judge limits, human-eval design,
data/concept drift, golden sets, statistical significance of eval deltas.

## Statistics / experimentation
Hypothesis testing, p-value & what it is NOT, confidence intervals, type I/II error, power &
sample size, A/B test design, guardrail metrics, multiple-comparisons correction, novelty/
primacy effects, SRM (sample-ratio mismatch) sanity check, effect size (never bare p).

## System-design approach (structured, say it out loud)
1. **Clarify** requirements, scale, constraints, the objective. Don't design before scoping.
2. **Define success** — the metric(s) and SLAs.
3. **High-level architecture** — data → features/extraction → model/logic → eval → serving.
4. **Drill the hard part** the interviewer cares about; state tradeoffs at each fork.
5. **Failure modes / drift / monitoring / scale** — show maturity.
6. **Summarize** the design and its main tradeoff. For ML-design: always cover data, labels,
   metric, baseline, validation, and online vs offline.

## Coding / DSA
Think-aloud is the graded behavior — narrate your approach before and while coding; a silent
correct solution scores worse than a narrated one. Pattern checklist: arrays/strings, hashmaps,
two-pointers/sliding-window, stacks/queues, trees/graphs (BFS/DFS), recursion/backtracking,
sorting, binary search, heaps, DP (start simple). For ML/AS roles also drill **ML-coding**:
implement a metric (precision/recall/AUC), k-means, gradient step, data-wrangling in
numpy/pandas. Always: clarify → examples/edge cases → brute force → optimize → state Big-O →
test on an example.

## Behavioral (STAR + L) + values
Enforce **Situation → Task → Action → Result → Learnings**, first-person ("I", not "we"),
**quantified results**, and an explicit learning. Build a **story bank** of 6–8 reusable
stories (a hard technical decision, a conflict, a failure, leadership/initiative, ambiguity,
impact) and map each to the company's stated values. Map to **Microsoft** values when relevant:
growth mindset (learn-it-all, "I got X wrong and changed it"), customer obsession, One
Microsoft (collaboration across teams), diversity & inclusion, making a difference. Overlearn
the anchors: **"tell me about yourself"** (a crisp 60–90s narrative arc, not a résumé readout)
and **"why this company/team/role."**

## Always prepare questions to ask THEM
3–5 thoughtful questions signal genuine interest and seniority: about the team's hardest
current problem, how success is measured, where the product is heading, what the interviewer
finds most challenging. Never "no questions."

## Pre-mortem seeds (classic interview failure modes)
Knew what but not why · froze on an open scenario · over-claimed a number · rambled with no
STAR · blanked on a fundamental · couldn't structure a design question · went silent in coding
· vague "tell me about yourself" · no questions for them · talked too low/high level.

## Rehearsal protocol
Active recall, out loud, under time pressure — never re-reading notes. Drill weakest cells
first. Mock with cold, out-of-order questions and hostile follow-ups; score each answer; feed
scores back into the readiness register. Spaced over the runway. 24h cutoff: consolidation +
rest, no new topics.

## Curated resources (recommend per need)
- **ML/DS interviews**: Chip Huyen *Introduction to ML Interviews* (free book) & *Designing
  ML Systems*; Alex Xu *Machine Learning System Design Interview* & *System Design Interview*.
- **Coding**: *Cracking the Coding Interview* (McDowell); NeetCode patterns; LeetCode.
- **Behavioral/STAR**: Amazon-style "leadership principles" prep generalizes well; the STAR+L
  structure.
- **Stats/experimentation**: Kohavi, Tang & Xu *Trustworthy Online Controlled Experiments*.
- **Mindset**: Annie Duke *Thinking in Bets* (reasoning under uncertainty); reappraise nerves
  as readiness (Brooks 2014).

## Anti-patterns
Memorizing answers instead of reasoning · over-claiming / inventing numbers · "we" instead of
"I" · unstructured rambling · designing before scoping · silent coding · low/high altitude
mismatch · no questions for them · cramming breadth the night before instead of consolidating.
