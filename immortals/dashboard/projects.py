"""Projects API for the Console (AS-032) — kgraph is the project context store.

A "project" in the Console is a **local filesystem folder** the agents work in. The list of
projects and each project's *context* (its knowledge map: components, decisions, facts) come from
**kgraph**, the per-user persistent knowledge-graph memory — we don't keep a separate store. This
module shells out to the kgraph CLI (path from ``config.projects_source()``, env-overridable) to:

- ``GET /api/projects`` — list projects (id, name, root, summary, node/edge counts).
- ``GET /api/projects/tree?root=…`` — the project's file tree (confined to a *registered* project
  root, with common noise like ``.git``/``node_modules`` pruned).
- ``GET /api/projects/file?root=…&path=…`` — read one file (confined; size-limited).
- ``GET /api/projects/context?root=…`` — the kgraph map for the project (its stored context).
- ``POST /api/projects`` — register/refresh a project's kgraph map (name + optional summary).

Security: file browsing is only allowed for roots that kgraph already knows (no arbitrary
filesystem access), plus a path-traversal guard inside the root.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from immortals import config

from fastapi import Body, HTTPException, Query

_IGNORE = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "dist-ssr", ".vite",
           ".mypy_cache", ".pytest_cache", ".idea", ".vscode", "build", ".next", "target"}
_MAX_ENTRIES_PER_DIR = 400
_MAX_DEPTH = 8
_MAX_FILE_BYTES = 400_000


def _run_kgraph(args: list[str], cwd: str | None = None) -> Any:
    """Invoke the kgraph CLI with ``--json`` and parse its stdout. Returns None on any failure."""
    kg = config.projects_source()
    if not Path(kg).exists():
        return None
    cmd = [sys.executable, str(kg), "--json"]
    if cwd:
        cmd += ["--cwd", cwd]
    cmd += args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return None


def list_projects() -> list[dict[str, Any]]:
    raw = _run_kgraph(["projects"]) or []
    out: list[dict[str, Any]] = []
    for p in raw:
        root = p.get("root_path")
        if not root:
            continue
        out.append({
            "id": p.get("key"),
            "name": p.get("name"),
            "root": root,
            "summary": p.get("summary"),
            "nodes": p.get("nodes", 0),
            "edges": p.get("edges", 0),
            "exists": Path(root).exists(),
        })
    return out


def _known_root(root: str) -> Path:
    """Resolve ``root`` only if it's a registered kgraph project root (else 404/403)."""
    known = {str(Path(p["root"]).resolve()) for p in list_projects()}
    resolved = Path(root).resolve()
    if str(resolved) not in known:
        raise HTTPException(status_code=403, detail="root is not a registered project")
    if not resolved.is_dir():
        raise HTTPException(status_code=404, detail="project root not found on disk")
    return resolved


def build_tree(root: Path, rel: Path = Path("."), depth: int = 0) -> dict[str, Any]:
    """A pruned, bounded file tree rooted at ``root`` (dirs first, alphabetical)."""
    abs_dir = root / rel if rel != Path(".") else root
    children: list[dict[str, Any]] = []
    try:
        entries = sorted(abs_dir.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        entries = []
    for entry in entries[:_MAX_ENTRIES_PER_DIR]:
        if entry.name in _IGNORE or entry.name.startswith("."):
            continue
        child_rel = (rel / entry.name) if rel != Path(".") else Path(entry.name)
        if entry.is_dir():
            node: dict[str, Any] = {"name": entry.name, "path": child_rel.as_posix(), "type": "dir"}
            if depth < _MAX_DEPTH:
                node["children"] = build_tree(root, child_rel, depth + 1)["children"]
            children.append(node)
        else:
            children.append({"name": entry.name, "path": child_rel.as_posix(), "type": "file"})
    return {"name": root.name if depth == 0 else abs_dir.name, "path": rel.as_posix(),
            "type": "dir", "children": children}


def _safe_file(root: Path, rel: str) -> Path:
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="path escapes the project root")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="not a file")
    return candidate


def _native_folder_dialog() -> str | None:
    """Open a native OS folder picker on the engine host and return the chosen absolute path.

    Runs a throwaway subprocess (its own Tk main loop) so it never blocks the server's event loop
    or fights the main thread. Local-first: the person at the machine physically chooses the folder;
    nothing lets a remote caller read arbitrary paths. Returns None if cancelled/unavailable.
    """
    code = (
        "import tkinter as tk\n"
        "from tkinter import filedialog\n"
        "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)\n"
        "print(filedialog.askdirectory(title='Select a project folder') or '')\n"
    )
    try:
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = (proc.stdout or "").strip()
    return out.splitlines()[-1].strip() if out else None


def attach_projects_api(app) -> None:
    @app.get("/api/projects")
    def get_projects() -> dict[str, Any]:
        return {"projects": list_projects()}

    @app.get("/api/projects/tree")
    def project_tree(root: str = Query(...)) -> dict[str, Any]:
        return build_tree(_known_root(root))

    @app.get("/api/projects/file")
    def project_file(root: str = Query(...), path: str = Query(...)) -> dict[str, Any]:
        base = _known_root(root)
        f = _safe_file(base, path)
        data = f.read_bytes()[:_MAX_FILE_BYTES]
        return {"path": path, "content": data.decode("utf-8", errors="replace"),
                "truncated": f.stat().st_size > _MAX_FILE_BYTES}

    @app.get("/api/projects/context")
    def project_context(root: str = Query(...)) -> dict[str, Any]:
        base = _known_root(root)
        ctx = _run_kgraph(["recall"], cwd=str(base))
        return {"root": str(base), "context": ctx}

    @app.post("/api/projects/browse")
    def browse_folder() -> dict[str, Any]:
        """Open a native folder picker on the engine host; returns the chosen path (or null)."""
        return {"root": _native_folder_dialog()}

    @app.post("/api/projects")
    def register_project(body: dict = Body(...)) -> dict[str, Any]:
        root = body.get("root")
        name = body.get("name")
        if not root or not name:
            raise HTTPException(status_code=422, detail="body needs 'root' and 'name'")
        if not Path(root).is_dir():
            raise HTTPException(status_code=400, detail="root is not an existing directory")
        args = ["project", "--name", name]
        if body.get("summary"):
            args += ["--summary", body["summary"]]
        if _run_kgraph(args, cwd=root) is None:
            raise HTTPException(status_code=502, detail="kgraph unavailable or failed")
        return {"ok": True, "root": root, "name": name}
