#!/usr/bin/env python3
"""AS-suite skills MCP server — lazy skill loading over MCP stdio.

Implements the progressive-disclosure design so a host loads only what it needs:

  * ``skill_list``          -> Tier-1 directory (name/description/owner/argument-hint), the
                               cheap always-on index; optionally scoped to one owner agent.
  * ``skill_get``           -> Tier-2: the full ``SKILL.md`` body, fetched only on demand.
  * ``skill_get_reference`` -> Tier-3: one ``references/`` or ``assets/`` file, on demand.

No third-party dependencies — newline-delimited JSON-RPC 2.0 over stdin/stdout, mirroring
``immortals/memory/mcp_server.py``. Portable: any MCP-capable host (Claude Code, Codex, Gemini
CLI, Cursor, Goose, ...) can mount it and get identical lazy-loading behaviour.

Run standalone:
    python -m immortals.skills_mcp                       # auto-locate skills/
    python -m immortals.skills_mcp --skills-dir <path>
    AS_SKILLS_DIR=<path> python -m immortals.skills_mcp
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2024-11-05"

# Tiny stopword set so free-text routing matches on meaningful tokens only (mirrors the
# registry loader's tokenizer, kept local to avoid a cross-module import in this standalone server).
_STOPWORDS = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you", "are", "was",
    "out", "can", "will", "use", "used", "using", "about", "what", "how", "why", "when", "who",
    "a", "an", "to", "of", "in", "on", "or", "is", "it", "as", "by", "be", "do", "my", "me", "i",
    "skill", "help", "need",
})


def _tokenize(text: str) -> set[str]:
    import re
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower())
            if len(t) > 2 and t not in _STOPWORDS}


def rank_skills(need: str, skills: list[dict], top: int | None = None) -> list[dict]:
    """Rank skills against a free-text ``need`` (deterministic, no LLM). Lets a lone agent load
    the ONE right skill body instead of scanning/loading several — the solo-agent efficiency win.

    Scores: skill-name token/phrase hit (heavy), description-token overlap (light). Returns
    ``[{name, score, owner_agent, description, argument_hint}, …]`` sorted by score desc, name.
    """
    need_lc = (need or "").lower()
    need_tokens = _tokenize(need)
    ranked = []
    for s in skills:
        name = s.get("name", "")
        score = 0
        name_phrase = name.replace("-", " ")
        name_tokens = _tokenize(name_phrase)
        if name_phrase and name_phrase in need_lc:
            score += 6
        elif name_tokens and name_tokens <= need_tokens:
            score += 4
        else:
            score += 2 * len(need_tokens & name_tokens)
        score += len(need_tokens & _tokenize(s.get("description", "")))
        if score > 0:
            ranked.append({
                "name": name,
                "score": score,
                "owner_agent": s.get("owner_agent"),
                "description": s.get("description", ""),
                "argument_hint": s.get("argument_hint"),
            })
    ranked.sort(key=lambda r: (-r["score"], r["name"]))
    return ranked[:top] if top else ranked


def resolve_skills_dir(argv: list[str]) -> Path:
    """--skills-dir wins, else $AS_SKILLS_DIR, else the repo's skills/ next to this package,
    else ./skills. Keeps the server usable both from the repo and when vendored elsewhere."""
    for i, tok in enumerate(argv):
        if tok == "--skills-dir" and i + 1 < len(argv):
            return Path(argv[i + 1])
        if tok.startswith("--skills-dir="):
            return Path(tok.split("=", 1)[1])
    env = os.environ.get("AS_SKILLS_DIR")
    if env:
        return Path(env)
    repo_skills = Path(__file__).resolve().parents[1] / "skills"
    if repo_skills.is_dir():
        return repo_skills
    return Path.cwd() / "skills"


# name -> (description, input-property -> json-type, required-property-names)
TOOLS: list[tuple[str, str, dict[str, str], list[str]]] = [
    ("skill_list",
     "The skill directory (Tier-1): list available skills with name, description, owner agent, "
     "and argument hint — the cheap index to scan before loading a body. Optionally filter to "
     "one owner agent (e.g. 'paperAS') to see only that agent's skills.",
     {"agent": "string"}, []),
    ("skill_get",
     "Load the FULL SKILL.md body for one skill by name (Tier-2) — do this only when the skill "
     "is actually needed for the task.",
     {"name": "string"}, ["name"]),
    ("skill_get_reference",
     "Load one supporting file for a skill (Tier-3): a references/ or assets/ path relative to "
     "the skill directory (e.g. 'references/equations.md', 'assets/resolve_refs.py').",
     {"name": "string", "path": "string"}, ["name", "path"]),
    ("skill_route",
     "Rank skills against a free-text need (deterministic) so you load the ONE most relevant "
     "skill body instead of scanning several. Returns ranked {name, score, owner_agent}. Call "
     "this, then skill_get the top result. Optionally scope to one owner agent.",
     {"need": "string", "agent": "string", "top": "integer"}, ["need"]),
]
TOOL_NAMES = {t[0] for t in TOOLS}


def tool_schemas() -> list[dict[str, Any]]:
    out = []
    for name, desc, props, required in TOOLS:
        out.append({
            "name": name,
            "description": desc,
            "inputSchema": {
                "type": "object",
                "properties": {k: {"type": t} for k, t in props.items()},
                "required": required,
            },
        })
    return out


def _load_index(skills_dir: Path) -> list[dict[str, Any]]:
    """Prefer the generated INDEX.json; fall back to a light on-the-fly scan if absent."""
    idx = skills_dir / "INDEX.json"
    if idx.exists():
        try:
            return json.loads(idx.read_text(encoding="utf-8")).get("skills", [])
        except Exception:
            pass
    skills = []
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        if (d / "SKILL.md").exists():
            skills.append({"name": d.name, "description": "", "owner_agent": None,
                           "argument_hint": None, "path": f"skills/{d.name}/SKILL.md"})
    return skills


def _safe_skill_dir(skills_dir: Path, name: str) -> Path | None:
    """Resolve <skills_dir>/<name>, guarding against path traversal in ``name``."""
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        return None
    d = (skills_dir / name).resolve()
    if skills_dir.resolve() not in d.parents and d != skills_dir.resolve():
        return None
    return d if d.is_dir() else None


def call_tool(skills_dir: Path, name: str, arguments: dict[str, Any] | None) -> tuple[str, bool]:
    args = arguments or {}
    try:
        missing = [r for (n, _d, _p, req) in TOOLS if n == name for r in req if r not in args]
        if missing:
            return json.dumps({"error": f"missing required argument(s): {missing}"}), True

        if name == "skill_list":
            skills = _load_index(skills_dir)
            agent = args.get("agent")
            if agent:
                skills = [s for s in skills if s.get("owner_agent") == agent]
            # Return only the lean routing fields — the point is a cheap directory.
            lean = [{
                "name": s.get("name"),
                "description": s.get("description", ""),
                "owner_agent": s.get("owner_agent"),
                "argument_hint": s.get("argument_hint"),
                "has_references": bool(s.get("references")),
                "has_assets": bool(s.get("assets")),
            } for s in skills]
            return json.dumps({"count": len(lean), "skills": lean}, ensure_ascii=False), False

        if name == "skill_route":
            skills = _load_index(skills_dir)
            agent = args.get("agent")
            if agent:
                skills = [s for s in skills if s.get("owner_agent") == agent]
            top = args.get("top")
            top = top if isinstance(top, int) and top > 0 else 3
            ranked = rank_skills(args["need"], skills, top=top)
            return json.dumps({"need": args["need"], "matches": ranked}, ensure_ascii=False), False

        if name == "skill_get":
            d = _safe_skill_dir(skills_dir, args["name"])
            if d is None:
                return json.dumps({"error": f"unknown skill: {args['name']!r}"}), True
            body = (d / "SKILL.md").read_text(encoding="utf-8-sig", errors="replace")
            return json.dumps({"name": args["name"], "content": body}, ensure_ascii=False), False

        if name == "skill_get_reference":
            d = _safe_skill_dir(skills_dir, args["name"])
            if d is None:
                return json.dumps({"error": f"unknown skill: {args['name']!r}"}), True
            rel = str(args["path"]).replace("\\", "/")
            target = (d / rel).resolve()
            if d.resolve() not in target.parents:  # traversal guard
                return json.dumps({"error": "path escapes skill directory"}), True
            if not target.is_file():
                return json.dumps({"error": f"no such file: {rel}"}), True
            content = target.read_text(encoding="utf-8-sig", errors="replace")
            return json.dumps({"name": args["name"], "path": rel, "content": content},
                              ensure_ascii=False), False

        return json.dumps({"error": f"unknown tool: {name}"}), True
    except Exception as exc:  # noqa: BLE001 — surface any failure as an MCP tool error
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"}), True


def dispatch(skills_dir: Path, msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    mid = msg.get("id")
    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL_VERSION
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": ver,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "as-skills", "version": "1.0.0"},
        }}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": tool_schemas()}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name not in TOOL_NAMES:
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32602, "message": f"unknown tool: {name}"}}
        text, is_error = call_tool(skills_dir, name, params.get("arguments"))
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": text}], "isError": is_error}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method and method.startswith("notifications/"):
        return None
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"method not found: {method}"}}
    return None


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    skills_dir = resolve_skills_dir(argv)
    out = sys.stdout
    try:
        out.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = dispatch(skills_dir, msg)
        if response is not None:
            out.write(json.dumps(response) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
