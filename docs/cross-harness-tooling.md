# Running the AS suite across harnesses — portable tooling landscape

> **Goal:** run the same `agents/` + `skills/` (individually or in combos) on hosts other than
> GitHub Copilot CLI — Claude Code, Codex, Gemini CLI, Cursor, etc. — using the
> **MCP-server-inspired lazy-load design** (a cheap index the agent scans; full skill bodies
> pulled into context only on demand) and **typed JSON-Schema contracts** at every seam.
>
> **The one idea:** keep a single *portable core* (agents + skills + contracts + registry) and
> generate *thin adapters* per host. MCP is the substrate every serious harness speaks, so the
> lazy-load and the quality gates port unchanged.

## What "portable" means here
A tool is a good fit if it supports:
1. **MCP** (Model Context Protocol, JSON-RPC 2.0) — so our `skills` / `memory` / `router`
   servers mount identically. This is the load-bearing requirement.
2. **A per-project instruction file** (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md` / rules) — the
   thin adapter we generate from one source.
3. Ideally **custom sub-agents** and a way to reference external skill files.

Only Claude Code has *native* Agent Skills (`SKILL.md`) today. **Everywhere else, our skills MCP
server _is_ the skills feature** — which is exactly why the MCP-inspired design is the
portability unlock, not merely a token optimization.

## Side-by-side comparison

| Tool | Vendor | License / OSS | Pricing model | MCP | Native skills | Agent-instruction file | Sub-agents |
|---|---|---|---|:--:|:--:|---|:--:|
| **Codex CLI** | OpenAI | **OSS (Apache-2.0)** | API usage / ChatGPT plans | ✅ | via MCP | `AGENTS.md` | limited |
| **Gemini CLI** | Google | **OSS (Apache-2.0)** | large free tier + API | ✅ | via MCP | `GEMINI.md` | limited |
| **opencode** | SST | **OSS (MIT)** | bring-your-own model/key | ✅ | via MCP | `AGENTS.md` | ✅ |
| **Goose** | Block | **OSS (Apache-2.0)** | bring-your-own model/key | ✅✅ (MCP-first "extensions") | via MCP | recipes | ✅ |
| **Cline** | Cline | **OSS** (VS Code ext) | bring-your-own key | ✅ | via MCP | rules | ✅ |
| **Roo Code** | Roo | **OSS** (Cline fork) | bring-your-own key | ✅ | via MCP | rules/modes | ✅ (modes) |
| **Kilo Code** | Kilo | **OSS** (VS Code ext) | bring-your-own key | ✅ | via MCP | rules | ✅ |
| **Continue** | Continue | **OSS** | bring-your-own key | ✅ | via MCP | rules | partial |
| **Aider** | Aider | **OSS (Apache-2.0)** | bring-your-own key | ✅ (newer) | via MCP | `CONVENTIONS.md` | ✗ |
| **Zed** | Zed Industries | **OSS** editor | free; hosts agents via **ACP** | ✅ | hosts other agents | — | via hosted agent |
| **Claude Code** | Anthropic | proprietary | **subscription** (Pro/Max) or API | ✅ | ✅ **native `SKILL.md`** | `CLAUDE.md` | ✅ |
| **Cursor** | Anysphere | proprietary | **subscription** | ✅ | via MCP | `.cursor/rules` | ✅ (agents) |
| **Windsurf** | Codeium | proprietary | **subscription** | ✅ | via MCP | rules / workflows | ✅ |
| **Amp** | Sourcegraph | proprietary | **subscription / usage** | ✅ | via MCP | `AGENTS.md` | ✅ |
| **GitHub Copilot CLI** | GitHub | proprietary | **subscription** | ✅ | ✅ (this repo) | agent `.md` | ✅ (Task) |

Legend: ✅ supported · ✅✅ first-class · via MCP = no native concept, use our skills MCP server.

## Recommended picks by intent

- **Fully open-source, provider-agnostic, no lock-in:** **Codex CLI** or **Gemini CLI** (both
  Apache-2.0, both MCP), or **opencode** / **Goose** if you want the strongest MCP-native +
  sub-agent story. Gemini CLI has the most generous free tier.
- **Best native skills experience (subscription):** **Claude Code** — the only host with
  first-class `SKILL.md`; our skills run natively *and* via the MCP server.
- **Editor-integrated:** **Cursor** (subscription, polished) or **Cline/Roo** (OSS, VS Code).
- **Agent-hosting / mix-and-match:** **Zed** via ACP can host Claude Code / Gemini as agents.

A portable core lets you use **several at once** and switch freely — that is itself the
anti-lock-in optimization.

## Fully open-source replacements for the proprietary hosts

If you want to drop the subscription hosts (Claude Code, Cursor, Copilot CLI) entirely, these
OSS tools cover the same ground — all speak MCP, so the `as-skills` server + adapters work
unchanged. (Grounded in 2026 reviews + benchmarks; see sources at the end.)

| Proprietary host | OSS alternative(s) | License | Native agent-switch | Notes |
|---|---|---|:--:|---|
| **Claude Code** | **opencode** | MIT | ✅ | closest drop-in; 75+ providers incl. local Ollama; ~180k★ |
| | **Codex CLI** | Apache-2.0 | ✅ | top benchmark accuracy; OpenAI-leaning; sandboxed |
| | **Goose** | Apache-2.0 | ✅ | MCP-first; automation beyond code (DevOps) |
| | **Gemini CLI** | Apache-2.0 | via file | large free tier |
| | **Aider** | Apache-2.0 | partial | git-surgical; in maintenance mode |
| **Cursor** | **Cline** | Apache-2.0 | ✅ | VS Code, approval-gated, GitHub integration |
| | **Roo Code / Kilo Code** | Apache-2.0 / OSS | ✅ | Cline-family VS Code extensions |
| | **Continue** | Apache-2.0 | partial | VS Code / JetBrains |
| | **Void / Zed** | OSS editors | via ACP | Void = OSS Cursor-like; Zed hosts agents |
| **GitHub Copilot CLI** | **opencode / Codex CLI / Goose** | — | ✅ | same CLI-first, agent-switching UX |

Only Claude Code has *native* `SKILL.md`; on every OSS host above, **our `as-skills` MCP server
is the skills feature**.

## Use-case suitability (suggestion %)

> **What the numbers mean (read this).** These are **synthesized suitability scores** — my own
> analysis weighted by 2026 developer reviews/benchmarks (opencode's autonomy + provider breadth,
> Codex's benchmark accuracy, Goose's MCP/automation depth, Cline's IDE+review flow, Aider's
> git-surgical safety). They are **recommendations, not measured benchmarks**; treat ±10% as
> noise and pick within a use-case's top cluster.

| Use case (for this suite) | opencode | Codex CLI | Goose | Cline | Aider | Gemini CLI |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **Run the full AS suite** (multi-agent + MCP skills) | **90%** | 70% | **88%** | 65% | 40% | 68% |
| **Heavy coding / large-repo refactor** (coderAS) | **88%** | 85% | 70% | 80% | 82% | 72% |
| **Local / offline / private / token-limited** | **92%** | 60% | 85% | 75% | 88% | 55% |
| **Surgical git edits / audits / safety-critical** | 75% | 70% | 60% | 80% | **92%** | 68% |
| **IDE-integrated workflow** | 60% | 55% | 45% | **92%** | 50% | 55% |
| **DevOps / automation beyond code** (managerAS ops) | 80% | 65% | **92%** | 55% | 45% | 70% |
| **Skills-heavy** (paperAS/researchAS/teachAS via MCP) | 88% | 78% | **90%** | 80% | 60% | 75% |
| **Raw model accuracy / speed** | 82% | **92%** | 72% | 78% | 75% | 80% |

### Bottom line by intent
- **Default all-rounder for this suite:** **opencode** (90–92% on orchestration, local, coding) —
  the strongest single drop-in.
- **If you live in MCP/automation or want managerAS driving ops:** **Goose** (MCP-first, 92%).
- **If you want maximum model accuracy and accept OpenAI-leaning:** **Codex CLI** (92% accuracy).
- **If you work in VS Code:** **Cline** (92% IDE fit).
- **If you want safe, auditable, low-cost git edits (great with local models):** **Aider** (92%
  git-surgical) — note it's in maintenance mode, so fewer new features.
- **Cheapest to start / big free tier:** **Gemini CLI**.

*Sources: 2026 comparisons and developer feedback — pinggy.io, rywalker.com, sanj.dev,
dev.to (moksh / jovan), morphllm Terminal-Bench, agentic.ai, devtoollab. Percentages are the
author's synthesis of those reviews plus fit-for-this-suite analysis, not a reproducible metric.*

## Standards to anchor on (so you never rebuild per tool)

| Standard | What it is | We use it for |
|---|---|---|
| **MCP** (JSON-RPC 2.0) | tool/resource/prompt transport, near-universal | `skills`, `memory`, `router` servers |
| **SKILL.md / Agent Skills** | open, portable skill format | our `skills/*/SKILL.md` |
| **AGENTS.md** | emerging cross-tool agent-instruction convention | generated adapter for Codex/opencode/Cursor/Amp |
| **JSON Schema** | typed contracts | `registry/v1`, `artifact/v1`, `plan/v1` — the model-independent quality floor |
| **ACP** (Agent Client Protocol) | editor↔agent hosting (Zed) | optional: host the suite inside Zed |
| **A2A** (Agent2Agent) | agent↔agent interop | optional: cross-process agent combos |

## How to optimize for this cross-harness setup (without losing quality)

1. **Single source of truth + generated adapters.** One `build-adapters` step emits
   `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` from the same agent + index data. No per-tool forks.
2. **MCP servers = the portability layer.** Skills, memory, and routing live behind MCP →
   identical behavior in every host. Progressive disclosure (index → get) is host-independent.
3. **Typed contracts at every seam = the quality guarantee that survives model swaps.** When you
   move Claude → GPT-5 → Gemini, JSON-Schema validation keeps each artifact correct regardless
   of model. This is the #1 defense against "works in one tool, breaks in another."
4. **Deterministic assets (scripts) over LLM reasoning** for exact work → same result
   everywhere, model-independent, ~0 tokens. (See `skills/*/assets/*.py`.)
5. **Registry-as-data routing** → the same `route(need)` logic ports because it's JSON + a tiny
   matcher, not tool-specific code.
6. **A conformance test suite** (`scripts/lint_prompts.py` + contract validation) as a CI gate →
   guarantees any artifact loads and validates in any MCP host before you ship it.
7. **Provenance + `version` on every artifact/skill** → reproducibility across hosts and models.

## Honest trade-offs

- **MCP maturity varies.** Goose / Cline / Codex / Gemini are strong; Aider is thinner. Test
  the servers against your top two hosts, not all fifteen.
- **OSS vs subscription** = control vs polish. OSS gives provider-agnostic + no lock-in;
  subscription gives native skills + UX. The portable core lets you have both.
- **Model variance is real.** The same skill prompt yields different quality across models;
  contracts + tests catch regressions — don't assume parity.
- **Two-hop lazy load** costs a tool round-trip per skill — worth it for large/selective skills,
  skip for tiny ones.

---

*This document is part of the portable layer. See also: `skills/INDEX.json` (the generated
directory), the skills MCP server, and the adapter generator.*
