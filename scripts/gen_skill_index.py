#!/usr/bin/env python3
"""Generate skills/INDEX.json — the always-on "directory" for lazy skill loading.

This is Tier-1 of the progressive-disclosure design: a compact index of every skill
(name + description + owner-agent + version + argument-hint + reference/asset listing) that an
agent (or the skills MCP server) scans cheaply. The full SKILL.md body is loaded on demand only
when a skill is actually needed (Tier-2), and references/assets only when their phase runs
(Tier-3).

Dependency-free (parses the leading `---` frontmatter block itself). Deterministic output
(sorted, stable key order) so the committed INDEX.json diffs cleanly.

Usage:
  python scripts/gen_skill_index.py            # write skills/INDEX.json
  python scripts/gen_skill_index.py --check     # exit 1 if INDEX.json is stale (CI gate)
  python scripts/gen_skill_index.py --stdout    # print, don't write
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"
INDEX_PATH = SKILLS_DIR / "INDEX.json"
CHARS_PER_TOKEN = 4

# Skills vendored unmodified from anthropics/skills (see skills/PROVENANCE.md).
VENDORED_SKILLS = frozenset({
    "skill-creator", "docx", "pdf", "xlsx", "mcp-builder", "webapp-testing",
    "frontend-design", "web-artifacts-builder", "canvas-design", "brand-guidelines",
    "theme-factory", "doc-coauthoring", "internal-comms",
})


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """(frontmatter, body). utf-8-sig upstream strips any BOM."""
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def get_field(fm: str, key: str) -> str | None:
    """Extract a top-level scalar/block field. Handles `key: v`, quoted, `>`/`|` block scalars,
    and multi-line double-quoted scalars."""
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}\s*:\s*(.*)$", line)
        if not m:
            continue
        val = m.group(1).strip()
        if val in (">", "|", ">-", "|-", ">+", "|+"):
            collected = []
            for nxt in lines[i + 1:]:
                if nxt.strip() == "" or nxt.startswith((" ", "\t")):
                    collected.append(nxt.strip())
                else:
                    break
            return " ".join(c for c in collected if c).strip()
        if val.startswith('"') and not (len(val) > 1 and val.endswith('"')):
            collected = [val[1:]]
            for nxt in lines[i + 1:]:
                if nxt.rstrip().endswith('"'):
                    collected.append(nxt.rstrip()[:-1])
                    break
                collected.append(nxt)
            return " ".join(c.strip() for c in collected).strip()
        return val.strip().strip('"').strip("'")
    return None


def rel_files(base: Path, subdir: str) -> list[str]:
    d = base / subdir
    if not d.is_dir():
        return []
    return sorted(f"{subdir}/{p.relative_to(d).as_posix()}"
                  for p in d.rglob("*") if p.is_file())


def build_index() -> dict:
    skills = []
    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        sm = skill_dir / "SKILL.md"
        if not sm.exists():
            continue
        text = sm.read_text(encoding="utf-8-sig", errors="replace")
        fm, body = split_frontmatter(text)
        fm = fm or ""
        name = get_field(fm, "name") or skill_dir.name
        entry = {
            "name": name,
            "description": get_field(fm, "description") or "",
            "owner_agent": get_field(fm, "owner-agent"),
            "version": get_field(fm, "version"),
            "argument_hint": get_field(fm, "argument-hint"),
            "path": f"skills/{skill_dir.name}/SKILL.md",
            "references": rel_files(skill_dir, "references"),
            "assets": rel_files(skill_dir, "assets"),
            "body_tokens_est": max(1, len(body) // CHARS_PER_TOKEN),
            "vendored": skill_dir.name in VENDORED_SKILLS,
        }
        skills.append(entry)
    return {
        "schema": "skill-index/v1",
        "generated_by": "scripts/gen_skill_index.py",
        "count": len(skills),
        "skills": skills,
    }


def dumps(index: dict) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if INDEX.json is stale")
    ap.add_argument("--stdout", action="store_true", help="print instead of writing")
    args = ap.parse_args()

    index = build_index()
    out = dumps(index)

    if args.stdout:
        sys.stdout.write(out)
        return 0
    if args.check:
        current = INDEX_PATH.read_text(encoding="utf-8") if INDEX_PATH.exists() else ""
        if current != out:
            print("skills/INDEX.json is stale — run: python scripts/gen_skill_index.py")
            return 1
        print(f"skills/INDEX.json up to date ({index['count']} skills).")
        return 0

    INDEX_PATH.write_text(out, encoding="utf-8")
    print(f"Wrote {INDEX_PATH.relative_to(REPO)} ({index['count']} skills).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
