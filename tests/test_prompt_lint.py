"""Guard the AS-suite prompt artifacts (agents/*.md, skills/*/SKILL.md).

Runs the dependency-free linter in-process and asserts there are no ERROR-level findings
(missing frontmatter, name/dir mismatch, missing description) and no interop drift between a
skill's owner-agent and the registry manifests. Warnings (style/size nudges) are allowed.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LINTER = REPO / "scripts" / "lint_prompts.py"


def _load_linter():
    spec = importlib.util.spec_from_file_location("lint_prompts", LINTER)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass annotation resolution (str | None) can find the module.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_no_errors_in_prompt_artifacts():
    lint = _load_linter()
    results = lint.collect()
    errors = {r.path: r.errors for r in results if r.errors}
    assert not errors, f"prompt-artifact lint errors: {errors}"


def test_no_interop_drift():
    lint = _load_linter()
    results = lint.collect()
    drift = lint.check_interop(results)
    assert not drift, f"skill<->registry interop drift: {drift}"


def test_every_skill_has_owner_and_version():
    lint = _load_linter()
    results = lint.collect()
    missing = []
    for r in results:
        if r.kind != "skill":
            continue
        name = Path(r.path).parent.name
        if name in lint.VENDORED_SKILLS:
            continue
        text = (REPO / r.path).read_text(encoding="utf-8-sig", errors="replace")
        if "owner-agent:" not in text or "version:" not in text:
            missing.append(name)
    assert not missing, f"native skills missing owner-agent/version: {missing}"


def test_skill_index_is_fresh():
    """skills/INDEX.json must match a fresh generation (the lazy-load directory can't drift)."""
    spec = importlib.util.spec_from_file_location(
        "gen_skill_index", REPO / "scripts" / "gen_skill_index.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    fresh = mod.dumps(mod.build_index())
    on_disk = (REPO / "skills" / "INDEX.json").read_text(encoding="utf-8")
    assert fresh == on_disk, "skills/INDEX.json is stale — run: python scripts/gen_skill_index.py"


def test_portable_adapters_are_fresh():
    """portable/ adapters must match a fresh generation from registry + index."""
    spec = importlib.util.spec_from_file_location(
        "gen_adapters", REPO / "scripts" / "gen_adapters.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    stale = []
    for rel, content in mod.build_all().items():
        p = REPO / "portable" / rel
        if not p.exists() or p.read_text(encoding="utf-8") != content:
            stale.append(rel)
    assert not stale, f"portable adapters stale: {stale} — run: python scripts/gen_adapters.py"


def test_skill_requires_targets_exist():
    """Every skill `requires:` entry must name a real skill (no dangling dep)."""
    lint = _load_linter()
    drift = lint.check_interop(lint.collect())
    dangling = [w for w in drift if "does not exist (deps)" in w]
    assert not dangling, f"dangling skill deps: {dangling}"
