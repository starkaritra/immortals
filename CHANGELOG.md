# Changelog

All notable changes to **Immortals** are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-10

### Added
- **discoverAS agent + `discovery-log` skill**: a heavy scientific-discovery / idea-generation
  worker that runs an internal lab-team ensemble (PI, Theorist, Skeptic, Experimentalist,
  Cross-domain Generalist, Scholar) and a generate→reflect→rank (Elo tournament)→evolve→meta-review
  **Discovery Loop** (modeled on Google's AI Co-Scientist, Claude Science, and VIRSCI/iMAD),
  adapted as an interactive partner. Ships `agents/discoverAS.md`, `registry/discoverAS.json`, and
  the `discovery-log` skill — a lightweight append-only `discovery-log.md` lab notebook so every
  session's thinking is recorded and revisitable. Regenerated `skills/INDEX.json` (30→31) and the
  `portable/` host adapters.
- **Model-provider settings store** (AS-035): a server-side `SettingsStore`
  (`immortals/dashboard/settings.py`) persists per-provider config
  `{id,label,adapter,base_url,api_key,model,enabled}` to a perms-restricted JSON file under the
  user's home. Ships a **suggested catalogue** (Anthropic, OpenAI, Gemini, Groq, OpenRouter,
  Together, DeepSeek, Ollama, LM Studio, vLLM) and a curated list of ~18 local Ollama models.
  Keys are stored server-side and **masked on read** (the browser never re-receives a full key).
  Endpoints: `GET /api/settings/catalog`, `GET/PUT/DELETE /api/settings/providers`,
  `POST /api/settings/providers/test` (live connectivity check against the posted config).
- **Local-model manager (Ollama)**: `GET /api/settings/ollama/status`, `/recommended`, and a
  streaming `POST /api/settings/ollama/pull` for one-click download of local models.
- **Delete a run from history**: `DELETE /api/runs/{id}` + `store.delete_task()` — deliberately
  bypasses the append-only event triggers for explicit user deletes only.
- **Standalone packaged engine** (AS-036 build): a PyInstaller spec + entry point
  (`packaging/immortals-engine.spec`, `packaging/engine_entry.py`) produce a self-contained
  `immortals-engine` binary that bundles `registry/`, `agents/`, `skills/`, and package data, and
  sets `IMMORTALS_HOME` to the bundle root — **no Python needed on the user's machine**. This is
  the sidecar the desktop app (immortals-console) spawns.
- **CI/CD** (AS-036): GitHub Actions — `ci.yml` runs `pytest` on a `{ubuntu, windows}` matrix on
  every push/PR; `release.yml` builds the standalone binary per OS on a `v*` tag (and via a manual
  `workflow_dispatch`) and attaches the archives to the GitHub Release.

### Changed
- **All model providers rewritten to raw HTTP** (AS-035, stdlib `urllib` via a shared
  `post_json()` in `runners/providers/base.py`) — Anthropic, OpenAI, Gemini, and Ollama no longer
  require any vendor SDK. The engine now depends only on `jsonschema` (core) + `fastapi`/`uvicorn`
  (dashboard), which is what makes a small, deterministic PyInstaller bundle possible. The
  per-provider SDK extras were dropped from `pyproject.toml`.
- **Rebranded `AgentSuite` → `Immortals`** (decision AS-028). The Python package
  `agentsuite/` is now `immortals/`, environment variables `AGENTSUITE_*` are now
  `IMMORTALS_*`, and the module entry point is `python -m immortals`. The `<name>AS.md`
  worker personas and the immutable `AS-NNN` decision anchors are intentionally retained:
  *Immortals is the orchestration system; the AS agents are "the immortals" it commands.*
- `pyproject.toml` now carries publish-ready metadata (license, authors, URLs, classifiers,
  keywords) and sources its version from `immortals.__version__` (single source of truth).

### Added (earlier this cycle)
- A console-script entry point: `immortals …` (equivalent to `python -m immortals …`).
- A top-level `--version` flag on the CLI.
- **Write API** for the Console: `POST /api/tasks` + `WS /ws/tasks/{id}` (AS-031), a direct-API
  `ApiRunner` backend with a workspace-confined, approval-gated tool harness (AS-030), projects
  API (AS-032), goal→plan orchestration `POST /api/orchestrate` (AS-033), and an authoring API to
  create agents & skills from the UI (AS-034).
- `LICENSE` (Apache-2.0), `CONTRIBUTING.md`, and this `CHANGELOG.md`.

## [0.0.1] - 2026-06-20

### Added
- Initial pre-release of the orchestration core (Phases 0–6):
  versioned JSON contracts (`plan/v1`, `artifact/v1`, `registry/v1`, `event/v1`); a
  capability registry with deterministic routing; a swappable `AgentRunner` (mock +
  headless-`copilot` Backend A); a deterministic DAG orchestrator with seam-contract
  validation, guardrails, approval gates, resume, bounded parallelism, and partial re-runs;
  an event-sourced SQLite memory substrate with a zero-dependency MCP server; and a derived
  knowledge graph + semantic vector index. 159 tests passing.

[Unreleased]: https://github.com/starkaritra/immortals/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/starkaritra/immortals/releases/tag/v0.0.1
