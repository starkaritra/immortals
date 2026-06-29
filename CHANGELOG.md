# Changelog

All notable changes to **Immortals** are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Rebranded `AgentSuite` → `Immortals`** (decision AS-028). The Python package
  `agentsuite/` is now `immortals/`, environment variables `AGENTSUITE_*` are now
  `IMMORTALS_*`, and the module entry point is `python -m immortals`. The `<name>AS.md`
  worker personas and the immutable `AS-NNN` decision anchors are intentionally retained:
  *Immortals is the orchestration system; the AS agents are "the immortals" it commands.*
- `pyproject.toml` now carries publish-ready metadata (license, authors, URLs, classifiers,
  keywords) and sources its version from `immortals.__version__` (single source of truth).

### Added
- A console-script entry point: `immortals …` (equivalent to `python -m immortals …`).
- A top-level `--version` flag on the CLI.
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
