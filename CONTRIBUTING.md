# Contributing to Immortals

Thanks for your interest in improving **Immortals** — a manager-orchestrated multi-agent
system over the AS agent suite. This guide covers the local setup and the project's
conventions so changes stay consistent and reviewable.

## Development setup

```pwsh
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest                       # full suite (currently 159 tests)
```

Requirements: Python ≥ 3.11. The `copilot` CLI and the `~/.copilot/agents/*AS.md` personas
are only needed for the live `copilot` backend; everything else (and all tests) runs with the
built-in `mock` backend and needs no external services.

## How the project is organized

- `immortals/` — the orchestrator package (`contracts/`, `registry/`, `runners/`,
  `orchestrator/`, `memory/`, `cli.py`, `config.py`).
- `agents/` — the source-of-truth `<name>AS.md` worker personas (synced into the copilot
  agents dir by `immortals agents install`).
- `registry/` — one `registry/v1` capability manifest per worker.
- `design/` — the canonical docs: `architecture.md` (normative spec), `plan.md` (phased build
  order), and `handoff.md` (current state **+ the ADR-style decision log**).

## Conventions (please follow)

- **Decisions are recorded as ADRs.** Any non-trivial or hard-to-reverse change gets an entry
  in `design/handoff.md` using the existing `AS-NNN` template (context → options → decision →
  rationale → consequences). **Anchors are immutable** — never renumber or reuse one; when a
  decision is superseded, keep the anchor and update its title/status.
- **Contracts are versioned API seams.** Changing a schema in `immortals/contracts/schemas/`
  is a versioned change with migration tests — don't mutate a contract in place silently.
- **No hard-coded thresholds or machine paths.** Quality targets and budgets are configurable
  inputs (guardrails), and every filesystem location resolves through `immortals/config.py`
  (env-overridable `IMMORTALS_*`).
- **Tests back every claim.** Add or update tests for new behavior, schema validation, and
  migrations; keep `pytest` green before opening a PR.
- **Commits are small, atomic, and explain *why*.** Keep each change scoped to its task; raise
  unrelated issues separately rather than bundling drive-by edits. Never commit secrets or
  generated artifacts (respect `.gitignore`).
- **Update the docs you touch.** If a change alters architecture or state, update
  `design/handoff.md` (and `architecture.md` where it's the normative spec) in the same PR.

## Reporting issues

Open a GitHub issue with: what you expected, what happened, the exact command, and the
environment (OS + Python version). For orchestrator runs, the `--events` output and the
`--db` event log are the most useful diagnostics.
