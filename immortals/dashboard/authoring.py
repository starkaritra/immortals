"""Authoring API — create new agents and skills from the Console (AS-034).

The Console can extend the suite: add an **agent** (a persona `agents/<name>.md` + a validated
`registry/<name>.json` capability manifest) or a **skill** (`skills/<name>/SKILL.md`, then the
skill index is regenerated). Writes go to the engine's asset dirs (env-overridable via
`immortals.config`), which are the source of truth `immortals agents install` syncs from.

Safety: names are restricted to a safe slug, existing agents/skills are never overwritten (409),
and the manifest is validated against `registry/v1` before anything is written.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from immortals import config
from immortals.contracts.validate import validate

from fastapi import Body, HTTPException

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,48}$")


def _skills_dir() -> Path:
    return config.home() / "skills"


def _safe_name(name: str | None) -> str:
    if not name or not _NAME.match(name):
        raise HTTPException(status_code=422, detail="name must match ^[A-Za-z][A-Za-z0-9_-]{0,48}$")
    return name


def _yaml_str(s: str) -> str:
    """Single-line, double-quote-safe YAML scalar (collapse whitespace, swap quotes)."""
    return re.sub(r"\s+", " ", s).replace('"', "'").strip()


def attach_authoring_api(app) -> None:
    @app.post("/api/agents")
    def create_agent(body: dict = Body(...)) -> dict[str, Any]:
        name = _safe_name(body.get("agent") or body.get("name"))
        summary = (body.get("summary") or "").strip()
        caps = body.get("capabilities") or []
        if not summary:
            raise HTTPException(status_code=422, detail="'summary' is required")
        if not isinstance(caps, list) or not caps:
            raise HTTPException(status_code=422, detail="at least one capability is required")

        reg_path = config.registry_dir() / f"{name}.json"
        persona_path = config.agents_dir() / f"{name}.md"
        if reg_path.exists() or persona_path.exists():
            raise HTTPException(status_code=409, detail=f"agent {name!r} already exists")

        manifest: dict[str, Any] = {
            "schema": "registry/v1", "agent": name, "summary": summary,
            "capabilities": [str(c) for c in caps],
        }
        for key in ("consumes", "produces", "skills"):
            if body.get(key):
                manifest[key] = [str(x) for x in body[key]]
        if body.get("when_to_use"):
            manifest["when_to_use"] = str(body["when_to_use"])
        if body.get("cost_hint") in ("low", "medium", "high"):
            manifest["cost_hint"] = body["cost_hint"]
        if body.get("approval_default") in ("required", "none"):
            manifest["approval_default"] = body["approval_default"]
        try:
            validate(manifest, "registry/v1")
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"invalid manifest: {exc}")

        persona_body = (body.get("persona") or f"You are {name}. {summary}").strip()
        persona = f'---\nname: {name}\ndescription: "{_yaml_str(summary)}"\n---\n\n{persona_body}\n'

        config.registry_dir().mkdir(parents=True, exist_ok=True)
        config.agents_dir().mkdir(parents=True, exist_ok=True)
        reg_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        persona_path.write_text(persona, encoding="utf-8")
        return {"ok": True, "agent": name}

    @app.post("/api/skills")
    def create_skill(body: dict = Body(...)) -> dict[str, Any]:
        name = _safe_name(body.get("name"))
        desc = (body.get("description") or "").strip()
        if not desc:
            raise HTTPException(status_code=422, detail="'description' is required")

        sdir = _skills_dir() / name
        if sdir.exists():
            raise HTTPException(status_code=409, detail=f"skill {name!r} already exists")

        lines = ["---", f"name: {name}", f'description: "{_yaml_str(desc)}"']
        if body.get("argument_hint"):
            lines.append(f'argument-hint: "{_yaml_str(str(body["argument_hint"]))}"')
        if body.get("owner_agent"):
            lines.append(f"owner-agent: {_safe_name(body['owner_agent'])}")
        lines += ["version: 1.0.0", "---", "", (body.get("body") or f"# {name}\n\n{desc}\n").strip(), ""]

        sdir.mkdir(parents=True)
        (sdir / "SKILL.md").write_text("\n".join(lines), encoding="utf-8")

        # Regenerate the lazy-loading skill index so the new skill is discoverable.
        gen = config.home() / "scripts" / "gen_skill_index.py"
        if gen.exists():
            try:
                subprocess.run([sys.executable, str(gen)], cwd=str(config.home()),
                              capture_output=True, timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                pass
        return {"ok": True, "skill": name}
