"""Tests for the authoring API (AS-034) — create agents & skills.

IMMORTALS_HOME/AGENTS_DIR/REGISTRY_DIR are redirected to a temp dir so nothing touches the real
suite assets. The skill-index regeneration is a no-op here (no scripts/ under the temp home).
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi", reason="dashboard extra not installed")
pytest.importorskip("httpx", reason="fastapi TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from immortals.dashboard.app import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    home = tmp_path / "suite"
    (home / "registry").mkdir(parents=True)
    (home / "agents").mkdir(parents=True)
    (home / "skills").mkdir(parents=True)
    monkeypatch.setenv("IMMORTALS_HOME", str(home))
    monkeypatch.setenv("IMMORTALS_REGISTRY_DIR", str(home / "registry"))
    monkeypatch.setenv("IMMORTALS_AGENTS_DIR", str(home / "agents"))
    return TestClient(create_app(str(tmp_path / "run.db"))), home


def test_create_agent_writes_manifest_and_persona(client):
    c, home = client
    r = c.post("/api/agents", json={
        "name": "reviewerAS", "summary": "Reviews code for bugs.",
        "capabilities": ["code_review", "bug_report"], "when_to_use": "review a diff",
        "cost_hint": "low",
    })
    assert r.status_code == 200 and r.json()["agent"] == "reviewerAS"
    manifest = json.loads((home / "registry" / "reviewerAS.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "registry/v1" and manifest["capabilities"] == ["code_review", "bug_report"]
    persona = (home / "agents" / "reviewerAS.md").read_text(encoding="utf-8")
    assert persona.startswith("---") and "name: reviewerAS" in persona


def test_create_agent_rejects_bad_name_and_missing_caps(client):
    c, _ = client
    assert c.post("/api/agents", json={"name": "bad name!", "summary": "x", "capabilities": ["a"]}).status_code == 422
    assert c.post("/api/agents", json={"name": "okAS", "summary": "x", "capabilities": []}).status_code == 422


def test_create_agent_no_overwrite(client):
    c, _ = client
    payload = {"name": "dupAS", "summary": "s", "capabilities": ["a"]}
    assert c.post("/api/agents", json=payload).status_code == 200
    assert c.post("/api/agents", json=payload).status_code == 409


def test_create_skill_writes_skill_md(client):
    c, home = client
    r = c.post("/api/skills", json={"name": "csv-cleaner", "description": "Clean messy CSVs.",
                                    "owner_agent": "coderAS", "argument_hint": "path to a CSV"})
    assert r.status_code == 200 and r.json()["skill"] == "csv-cleaner"
    md = (home / "skills" / "csv-cleaner" / "SKILL.md").read_text(encoding="utf-8")
    assert "name: csv-cleaner" in md and "owner-agent: coderAS" in md and "version: 1.0.0" in md


def test_create_skill_no_overwrite_and_validation(client):
    c, _ = client
    ok = {"name": "dup-skill", "description": "d"}
    assert c.post("/api/skills", json=ok).status_code == 200
    assert c.post("/api/skills", json=ok).status_code == 409
    assert c.post("/api/skills", json={"name": "x", "description": ""}).status_code == 422
