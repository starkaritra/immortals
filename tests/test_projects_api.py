"""Tests for the kgraph-backed projects API (AS-032).

kgraph is stubbed via IMMORTALS_KGRAPH pointing at a fake CLI script, so these run with no real
kgraph install and no network. File-tree confinement + traversal guards are covered.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="dashboard extra not installed")
pytest.importorskip("httpx", reason="fastapi TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from immortals.dashboard.app import create_app  # noqa: E402
from immortals.dashboard import projects as projmod  # noqa: E402


@pytest.fixture
def project_root(tmp_path):
    root = tmp_path / "proj"
    (root / "src").mkdir(parents=True)
    (root / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "node_modules").mkdir()  # should be pruned from the tree
    (root / "node_modules" / "junk.js").write_text("x", encoding="utf-8")
    return root


@pytest.fixture
def fake_kgraph(tmp_path, project_root, monkeypatch):
    """A tiny fake kgraph CLI that emits the projects list this root belongs to."""
    payload = [{"id": 1, "key": "demo-key", "name": "Demo", "root_path": str(project_root),
                "summary": "a demo project", "nodes": 3, "edges": 2}]
    script = tmp_path / "fake_kgraph.py"
    script.write_text(
        "import sys, json\n"
        f"PAYLOAD = {json.dumps(payload)}\n"
        "args = [a for a in sys.argv[1:] if a != '--json']\n"
        "print(json.dumps(PAYLOAD if 'projects' in args else {'ok': True}))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("IMMORTALS_KGRAPH", str(script))
    return script


@pytest.fixture
def client(tmp_path, fake_kgraph):
    return TestClient(create_app(str(tmp_path / "run.db")))


def test_list_projects(client, project_root):
    data = client.get("/api/projects").json()
    assert data["projects"][0]["name"] == "Demo"
    assert data["projects"][0]["root"] == str(project_root)


def test_tree_prunes_noise(client, project_root):
    tree = client.get("/api/projects/tree", params={"root": str(project_root)}).json()
    names = {c["name"] for c in tree["children"]}
    assert "src" in names and "README.md" in names
    assert "node_modules" not in names  # pruned


def test_file_read_confined(client, project_root):
    ok = client.get("/api/projects/file", params={"root": str(project_root), "path": "src/main.py"})
    assert ok.status_code == 200 and "print" in ok.json()["content"]
    esc = client.get("/api/projects/file", params={"root": str(project_root), "path": "../secret"})
    assert esc.status_code in (400, 404)


def test_unregistered_root_forbidden(client, tmp_path):
    other = tmp_path / "not-a-project"
    other.mkdir()
    assert client.get("/api/projects/tree", params={"root": str(other)}).status_code == 403


def test_kgraph_absent_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTALS_KGRAPH", str(tmp_path / "does_not_exist.py"))
    assert projmod.list_projects() == []


def test_browse_returns_dialog_path(client, tmp_path, monkeypatch):
    monkeypatch.setattr(projmod, "_native_folder_dialog", lambda: str(tmp_path / "picked"))
    assert client.post("/api/projects/browse").json()["root"] == str(tmp_path / "picked")


def test_browse_cancelled_returns_null(client, monkeypatch):
    monkeypatch.setattr(projmod, "_native_folder_dialog", lambda: None)
    assert client.post("/api/projects/browse").json()["root"] is None


def test_register_project(client, tmp_path):
    newdir = tmp_path / "fresh"
    newdir.mkdir()
    r = client.post("/api/projects", json={"name": "Fresh", "root": str(newdir), "summary": "s"})
    assert r.status_code == 200 and r.json()["ok"] is True


def test_register_rejects_missing_dir(client, tmp_path):
    r = client.post("/api/projects", json={"name": "X", "root": str(tmp_path / "nope")})
    assert r.status_code == 400
