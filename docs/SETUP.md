# Setup & usage guide — AS agent suite (portable, MCP-based)

This is the **step-by-step** guide to installing and running the AS agent suite — the agents in
`agents/` and the skills in `skills/` — on GitHub Copilot CLI **and** on other MCP-capable hosts
(Claude Code, Codex, Gemini CLI, Cursor, Goose, opencode, …). It covers what to do, the exact
steps per host, and — just as important — **what _not_ to do**.

If you only read one thing: **keep one source of truth (this repo), load skills lazily through
the MCP server, and never hand-edit generated files.**

---

## 0. Concepts in 60 seconds

- **Agent** — a persona (`agents/<name>.md`) the host loads as its system prompt. You pick one
  (or combine several) for a task.
- **Skill** — a self-contained capability pack (`skills/<name>/SKILL.md` + optional
  `references/` and `assets/`). Agents call skills on demand.
- **Lazy loading (the whole point)** — a host does *not* load all skill bodies. It scans a cheap
  **index** (`skills/INDEX.json`), then pulls one skill body into context only when needed. Three
  tiers: `skill_list` (directory) → `skill_get` (one body) → `skill_get_reference` (one deep file).
- **MCP server** — `immortals/skills_mcp.py` serves those three tiers over MCP. This is how any
  host gets skills, even hosts with no native "skills" concept.
- **Typed contracts** — JSON Schemas in `immortals/contracts/schemas/` validate every artifact so
  quality holds when you swap host or model.

---

## 1. Prerequisites

- **Python ≥ 3.11** on `PATH` (`python --version`).
- **git**.
- The host you want to run in (Copilot CLI, Claude Code, Codex, Gemini CLI, Cursor, …).
- No third-party Python packages are required for the skills MCP server or the generators
  (standard library only). `pip install -e .` is only needed if you want the `immortals`
  orchestrator CLI.

---

## 2. Install the repo (one time)

```bash
git clone <this-repo-url> immortals
cd immortals

# optional: install the orchestrator CLI (adds `python -m immortals ...`)
pip install -e .

# sanity check
python scripts/lint_prompts.py          # should report 0 errors
python -m pytest -q                      # should be all green
```

**Do:** clone once and treat this repo as the single source of truth.
**Don't:** copy individual `SKILL.md` files around by hand — you'll get drift. Vendor the whole
`skills/` dir or point hosts at it via `AS_SKILLS_DIR` (below).

---

## 3. Regenerate the derived files (whenever you change agents/skills)

Two generated artifacts must stay in sync with the source. Both have a `--check` mode used by CI.

```bash
python scripts/gen_skill_index.py        # rebuild skills/INDEX.json (the lazy-load directory)
python scripts/gen_adapters.py           # rebuild portable/ host adapters + MCP snippets
```

**Do:** run these after adding/editing any skill or agent, then commit the result.
**Don't:** hand-edit `skills/INDEX.json` or anything under `portable/` — they're generated. Edit
the source (`skills/*/SKILL.md`, `registry/*.json`) and regenerate. The tests
`test_skill_index_is_fresh` / `test_portable_adapters_are_fresh` will fail if you forget.

---

## 4. Run in GitHub Copilot CLI

The agents already live in this repo's `agents/`. To make them selectable:

```bash
# copy personas into the copilot agents dir (~/.copilot/agents)
python -m immortals agents install
# then, per session:
copilot --agent managerAS        # or coderAS, teachAS, paperAS, ...
```

Skills in `~/.copilot/skills/` are auto-discovered by Copilot CLI. To also serve them lazily via
MCP (recommended for token-limited work), register the MCP server — see §6.

---

## 5. Run in other hosts (Claude Code / Codex / Gemini CLI / Cursor / …)

Each host needs two things: **(a)** an instruction file at the project root, and **(b)** the MCP
servers registered. Both are generated for you under `portable/`.

### 5.1 Pick and place the instruction file
| Host | Copy this to your project root |
|---|---|
| Claude Code | `portable/CLAUDE.md` → `CLAUDE.md` |
| Codex / opencode / Cursor / Amp | `portable/AGENTS.md` → `AGENTS.md` |
| Gemini CLI | `portable/GEMINI.md` → `GEMINI.md` |

```bash
cp portable/AGENTS.md /path/to/your/project/AGENTS.md    # example for Codex
```

### 5.2 Register the MCP servers
| Host | Use this snippet | Where it goes |
|---|---|---|
| Claude Code / Cursor | `portable/mcp/claude.mcp.json` | project `.mcp.json` (or `claude mcp add`) |
| Codex | `portable/mcp/codex.config.toml` | `~/.codex/config.toml` |
| Gemini CLI | `portable/mcp/gemini.settings.json` | `.gemini/settings.json` |

If the `skills/` directory is **not** next to the running process, tell the server where it is:

```bash
export AS_SKILLS_DIR=/absolute/path/to/immortals/skills
```
(or pass `--skills-dir <path>` in the server `args`).

### 5.3 Verify the MCP server is live
```bash
# quick manual check — should print the tool list
python -m immortals.skills_mcp --skills-dir ./skills <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
EOF
```
You should see `skill_list`, `skill_get`, `skill_get_reference`.

---

## 6. MCP server registration reference

Both servers are stdlib-only and launched by module:

```json
{
  "mcpServers": {
    "as-skills":  { "command": "python", "args": ["-m", "immortals.skills_mcp"] },
    "as-memory":  { "command": "python", "args": ["-m", "immortals.memory.mcp_server"] }
  }
}
```
- `as-skills` — lazy skill loading (`skill_list` / `skill_get` / `skill_get_reference`).
- `as-memory` — shared blackboard + notes + event log (for multi-agent runs; optional for solo).

**Do:** set `AS_SKILLS_DIR` when vendoring the suite into another repo.
**Don't:** register the server with a relative `skills/` path if the host's working directory
differs from where `skills/` lives — use an absolute `AS_SKILLS_DIR`.

---

## 7. Using the suite (the intended loop)

### Solo agent
1. Start the host with an agent instruction file / `--agent`.
2. The agent, when it needs a capability, calls `skill_list` (optionally scoped to itself:
   `skill_list(agent="paperAS")`), reads the descriptions, and calls `skill_get(name)` for the
   one it needs.
3. It runs the skill, pulling `skill_get_reference` only for deep detail.

### Combo / orchestrated
1. Give the task to **managerAS**.
2. It routes with the registry: `python -m immortals route --need "<task>" --pretty` returns
   ranked agents **and the skills each owns**, so it knows what to `skill_get`.
3. It emits a typed `plan/v1` and runs it through the orchestrator with a shared memory DB:
   ```bash
   python -m immortals run --plan-file plan.json --backend copilot --db run.db --pretty
   ```

---

## 8. Token-limited / long runs (avoid hitting the limit mid-work)

**Do:**
- Always run orchestrated work with `--db` so every finished node persists; on a limit-hit,
  `--resume` / `--from` continues **without redoing** completed work.
- Keep plans as **many small nodes**, not a few huge ones — a killed run loses ≤1 node.
- Prefer the skills' **executable assets** (`skills/*/assets/*.py`) over asking the model to do
  exact work — they cost ~0 model tokens and are reproducible.
- Scope skill listing by owner (`skill_list(agent=...)`) so only a handful of descriptions load.

**Don't:**
- Don't preload every skill body "just in case" — that defeats the whole design.
- Don't inline large prior outputs into the next prompt; reference them by artifact id via the
  memory server.
- Don't disable checkpointing (`--db`) on a long run to "save a little overhead" — you'll lose
  far more when the limit hits.

---

## 9. Adding or changing a skill (the safe procedure)

1. Create `skills/<name>/SKILL.md` with frontmatter: `name`, `description` (include *when to
   use* + *do NOT use*), `owner-agent`, `version`, optional `argument-hint`.
2. Put deep detail in `references/`, runnable helpers in `assets/` — keep the body lean.
3. If the skill is owned by an agent, add its name to that agent's `registry/<agent>.json`
   `skills` list.
4. Regenerate: `python scripts/gen_skill_index.py && python scripts/gen_adapters.py`.
5. Validate: `python scripts/lint_prompts.py && python -m pytest -q`.
6. Commit source + generated files together.

**Do:** write the `description` for routing — it's the only thing loaded before the body, so it
must carry the trigger phrases and the negative boundary.
**Don't:** duplicate another skill's scope without adding a "do NOT use / use X instead" clause —
it causes routing collisions.

---

## 10. Quality gates (run before you commit / ship)

```bash
python scripts/lint_prompts.py            # frontmatter, triggers, structure, interop drift
python scripts/gen_skill_index.py --check # index not stale
python scripts/gen_adapters.py --check    # adapters not stale
python -m pytest -q                        # full suite incl. contract validation
```
All four should pass. The linter is also exercised as a test (`tests/test_prompt_lint.py`), so a
plain `pytest` covers the gates.

---

## 11. Global do / don't cheat-sheet

**Do**
- Keep one source of truth (this repo); vendor whole directories, not stray files.
- Load skills lazily via the MCP server; scope by owner agent.
- Regenerate `INDEX.json` + `portable/` after any change, and commit them.
- Validate artifacts against the JSON-Schema contracts — that's the model-independent quality
  floor.
- Use `--db` + small nodes for any long/token-limited run.
- Author commits as the repo owner; get sign-off before pushing (see the `git-pr-workflow` skill).

**Don't**
- Don't hand-edit generated files (`skills/INDEX.json`, `portable/*`).
- Don't preload all skill bodies; don't inline stale context.
- Don't fork per host — generate thin adapters from the one source.
- Don't add a skill without a `description` that says when to use **and** when not to.
- Don't commit secrets or vendored-skill edits (keep `anthropics/skills` byte-identical).
- Don't assume model parity across hosts — let contracts + tests catch regressions.

---

## 12. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Host can't find skills | wrong working dir | set `AS_SKILLS_DIR` to an absolute path |
| `INDEX.json is stale` test fails | edited a skill, didn't regenerate | `python scripts/gen_skill_index.py` |
| `portable adapters stale` test fails | edited registry/index, didn't regenerate | `python scripts/gen_adapters.py` |
| Skill never activates | weak `description` | add explicit trigger phrases to frontmatter |
| Two skills both fire | overlapping scope | add a "do NOT use / use X instead" boundary |
| Lint reports interop drift | skill `owner-agent` not in registry `skills` | update the manifest, or the frontmatter |
| MCP server prints nothing | not sent a JSON-RPC line | send `initialize` first (newline-delimited JSON) |

---

*See also: `README.md` (architecture), `docs/cross-harness-tooling.md` (host landscape),
`portable/README.md` (adapter details), `skills/PROVENANCE.md` (native vs vendored skills).*
