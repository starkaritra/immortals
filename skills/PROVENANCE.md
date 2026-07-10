# Vendored & native skills — provenance

The `skills/` directory holds two kinds of capability packs:

## 1. Native AS-suite skills (authored for this project)
Owned and maintained in this repo; they encode the AS agents' own methodology.

- `lecture-notes`, `paper-explainer`, `paper-poster`, `prep-interview`,
  `prep-presentation`, `present-pitch-script`, `resume-optimizer` — the original suite.
- `git-pr-workflow` — coderAS VC hygiene + approval gate (rules 18–20).
- `latex-build` — LaTeX → PDF build + error triage (paperAS / paper-poster).
- `citation-verify` — reference integrity / hallucinated-citation checks (paperAS).
- `literature-search` — structured landscape / novelty scans (researchAS).
- `data-analysis-plots` — effect-size + CI stats and figures (experimentAS).
- `interactive-explorable` — single-file HTML explorables (teachAS).
- `novelty-log` — running novel-vs-prior-art ledger (researchAS / paperAS / patentAS).
- `discovery-log` — lightweight append-only lab-notebook of a discovery effort (discoverAS).
- `patent-claim-drafter`, `prior-art-search` — claim drafting + §102/§103 search (patentAS).
- `plan-synthesis-report` — BLUF run-synthesis brief (managerAS).

## 2. Vendored from `anthropics/skills`
Copied unmodified from the official Anthropic skills repository
(<https://github.com/anthropics/skills>). Their upstream license and any third-party
component licenses apply — see `THIRD_PARTY_NOTICES.md` (e.g. the OFL fonts bundled with
`canvas-design`).

- `skill-creator`, `docx`, `pdf`, `xlsx`, `mcp-builder`, `webapp-testing`,
  `frontend-design`, `web-artifacts-builder`, `canvas-design`, `brand-guidelines`,
  `theme-factory`, `doc-coauthoring`, `internal-comms`.

`pptx` was intentionally **not** vendored — it overlaps presentAS's own YAML→PPTX+reveal.js
pipeline.
