#!/usr/bin/env python3
"""Lint the AS-suite prompt artifacts (agents/*.md and skills/*/SKILL.md).

Dependency-free (no PyYAML): parses only the leading `---` frontmatter block and
the markdown body. Reports, per artifact, the signals the optimization arms care about:

  * Arm G (consistency): frontmatter present, `name` matches dir/file, required fields.
  * Arm A (activation):  description carries when-to-use / trigger / negative-boundary signal.
  * Arm B (token econ):  body size (lines + rough token estimate) vs a budget.
  * structure:           presence of the standard SKILL.md sections.

Exit code is non-zero if any ERROR-level check fails, so it can gate CI. It never
enforces a metric threshold as a hard fail (per the project's no-hard-gate rule);
size/трigger budgets are reported as warnings only.

Usage:
  python scripts/lint_prompts.py            # human report
  python scripts/lint_prompts.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO / "agents"
SKILLS_DIR = REPO / "skills"

# Rough token estimate: ~4 chars/token is the standard back-of-envelope for English.
CHARS_PER_TOKEN = 4
# Soft budget for the always-loaded SKILL.md body (Arm B). Warn, don't fail, above this.
# Rationale: SKILL.md should stay lean and push deep implementation detail into references/
# (progressive disclosure). Rich end-to-end workflow skills legitimately reach a few thousand
# tokens; the budget flags artifacts that should consider splitting, not a hard limit.
BODY_TOKEN_BUDGET = 3500

# Skills vendored unmodified from anthropics/skills (see skills/PROVENANCE.md). We do NOT
# restructure or re-budget these — upstream owns them — so deep checks are skipped for them.
VENDORED_SKILLS = frozenset({
    "skill-creator", "docx", "pdf", "xlsx", "mcp-builder", "webapp-testing",
    "frontend-design", "web-artifacts-builder", "canvas-design", "brand-guidelines",
    "theme-factory", "doc-coauthoring", "internal-comms",
})

# Signals that a description tells the model WHEN to fire (Arm A).
WHEN_SIGNALS = ("when to use", "use when", "use this", "triggers on", "trigger phrases")
NEGATIVE_SIGNALS = ("do not use", "don't use", "not for", "skip ", "do NOT")

# Standard SKILL.md sections we want (structure check). Matched case-insensitively.
SKILL_SECTIONS = ("when to use", "guardrail", "handoff")


@dataclass
class Result:
    path: str
    kind: str  # "agent" | "skill"
    name: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    body_tokens: int = 0
    body_lines: int = 0


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_block, body). Frontmatter is the text between the first
    two `---` fences at the very top of the file."""
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def get_field(fm: str, key: str) -> str | None:
    """Extract a top-level scalar/block field value from the frontmatter text.
    Handles `key: value`, `key: "value"`, and `key: >` / `key: |` block scalars."""
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}\s*:\s*(.*)$", line)
        if not m:
            continue
        val = m.group(1).strip()
        if val in (">", "|", ">-", "|-", ">+", "|+"):
            # Block scalar: gather subsequent more-indented lines.
            collected = []
            for nxt in lines[i + 1:]:
                if nxt.strip() == "" or nxt.startswith((" ", "\t")):
                    collected.append(nxt.strip())
                else:
                    break
            return " ".join(c for c in collected if c).strip()
        # Multi-line double-quoted scalar: opening quote with no closing quote on this
        # line — keep consuming physical lines until the closing quote.
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


def lint_file(path: Path, kind: str, expected_name: str, vendored: bool = False) -> Result:
    r = Result(path=str(path.relative_to(REPO)), kind=kind)
    # utf-8-sig strips a leading BOM so frontmatter detection is robust to editor quirks.
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    fm, body = split_frontmatter(text)

    r.body_lines = body.count("\n") + 1
    r.body_tokens = max(1, len(body) // CHARS_PER_TOKEN)

    if fm is None:
        r.errors.append("missing YAML frontmatter (no leading --- block)")
        return r

    name = get_field(fm, "name")
    r.name = name
    if not name:
        r.errors.append("frontmatter missing `name`")
    elif name != expected_name:
        r.errors.append(f"`name` is '{name}' but dir/file is '{expected_name}'")

    desc = get_field(fm, "description")
    if not desc:
        r.errors.append("frontmatter missing `description`")

    # Vendored skills: integrity only (name + description present). Skip Arm A/B/structure
    # nudges — we intentionally keep them byte-identical to upstream.
    if vendored:
        return r

    if desc:
        low = desc.lower()
        if not any(s in low for s in WHEN_SIGNALS):
            r.warnings.append("description lacks a 'when to use'/'triggers on' signal (Arm A)")
        if not any(s.lower() in low for s in NEGATIVE_SIGNALS):
            r.warnings.append("description lacks a 'do NOT use' negative boundary (Arm A)")

    # Arm G: version + owner metadata (new schema fields — warn until adopted).
    if get_field(fm, "version") is None:
        r.warnings.append("frontmatter missing `version` (Arm G schema)")
    if kind == "skill" and get_field(fm, "owner-agent") is None:
        r.warnings.append("frontmatter missing `owner-agent` (Arm G schema)")

    # Arm B: body token budget applies to SKILLS only (agents are whole personas, not
    # progressively-disclosed capability packs).
    if kind == "skill" and r.body_tokens > BODY_TOKEN_BUDGET:
        r.warnings.append(
            f"body ~{r.body_tokens} tokens > budget {BODY_TOKEN_BUDGET} — "
            "consider moving depth into references/ (Arm B)"
        )

    # Structure: standard SKILL.md sections (native skills only; vendored returned above).
    if kind == "skill":
        body_low = body.lower()
        for sec in SKILL_SECTIONS:
            if sec not in body_low:
                r.warnings.append(f"missing a '{sec}' section (structure)")

    return r


def collect() -> list[Result]:
    results: list[Result] = []
    for md in sorted(AGENTS_DIR.glob("*.md")):
        results.append(lint_file(md, "agent", md.stem))
    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        sm = skill_dir / "SKILL.md"
        if sm.exists():
            results.append(lint_file(sm, "skill", skill_dir.name,
                                     vendored=skill_dir.name in VENDORED_SKILLS))
        else:
            r = Result(path=str(skill_dir.relative_to(REPO)), kind="skill")
            r.errors.append("no SKILL.md in skill directory")
            results.append(r)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    results = collect()
    n_err = sum(len(r.errors) for r in results)
    n_warn = sum(len(r.warnings) for r in results)

    if args.json:
        print(json.dumps([r.__dict__ for r in results], indent=2))
        return 1 if n_err else 0

    print(f"Linted {len(results)} artifacts  "
          f"({sum(r.kind=='agent' for r in results)} agents, "
          f"{sum(r.kind=='skill' for r in results)} skills)\n")
    for r in results:
        if not r.errors and not r.warnings:
            print(f"  ok   {r.path}  (~{r.body_tokens} tok)")
            continue
        flag = "ERR " if r.errors else "warn"
        print(f"  {flag} {r.path}  (~{r.body_tokens} tok)")
        for e in r.errors:
            print(f"        ERROR:   {e}")
        for w in r.warnings:
            print(f"        warn:    {w}")
    print(f"\nSummary: {n_err} error(s), {n_warn} warning(s) across {len(results)} artifacts.")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
