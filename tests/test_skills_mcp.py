"""Tests for the AS-suite skills MCP server (lazy skill loading)."""

from __future__ import annotations

import json

from immortals import skills_mcp
from immortals.skills_mcp import call_tool, dispatch, resolve_skills_dir

SKILLS = resolve_skills_dir([])


def _call(name, args=None):
    text, is_error = call_tool(SKILLS, name, args or {})
    return json.loads(text), is_error


def test_initialize_and_tools_list():
    init = dispatch(SKILLS, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["serverInfo"]["name"] == "as-skills"
    tl = dispatch(SKILLS, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in tl["result"]["tools"]}
    assert names == {"skill_list", "skill_get", "skill_get_reference", "skill_route"}


def test_skill_list_returns_directory():
    data, err = _call("skill_list")
    assert not err
    assert data["count"] >= 27  # 17 native + vendored
    assert all("description" in s and "name" in s for s in data["skills"])


def test_skill_list_scoped_by_owner():
    data, err = _call("skill_list", {"agent": "paperAS"})
    assert not err
    names = {s["name"] for s in data["skills"]}
    assert {"citation-verify", "latex-build", "paper-explainer", "paper-poster"} <= names
    assert all(s["owner_agent"] == "paperAS" for s in data["skills"])


def test_skill_get_returns_full_body():
    data, err = _call("skill_get", {"name": "citation-verify"})
    assert not err
    assert data["content"].startswith("---")
    assert "citation-verify" in data["content"]


def test_skill_get_unknown_is_error():
    _data, err = _call("skill_get", {"name": "does-not-exist"})
    assert err


def test_skill_get_reference():
    data, err = _call("skill_get_reference",
                      {"name": "paper-explainer", "path": "references/equations.md"})
    assert not err
    assert len(data["content"]) > 0


def test_reference_path_traversal_blocked():
    _data, err = _call("skill_get_reference",
                       {"name": "paper-explainer", "path": "../../pyproject.toml"})
    assert err


def test_skill_name_traversal_blocked():
    _data, err = _call("skill_get", {"name": "../agents"})
    assert err


def test_skill_route_ranks_by_need():
    data, err = _call("skill_route", {"need": "verify the citations in my bibliography", "top": 3})
    assert not err
    assert data["matches"], "expected at least one match"
    assert data["matches"][0]["name"] == "citation-verify"
    # deterministic: sorted by score desc
    scores = [m["score"] for m in data["matches"]]
    assert scores == sorted(scores, reverse=True)


def test_skill_route_scoped_by_agent():
    data, err = _call("skill_route", {"need": "make a conference poster", "agent": "paperAS"})
    assert not err
    assert all(m["owner_agent"] == "paperAS" for m in data["matches"])
    assert "paper-poster" in {m["name"] for m in data["matches"]}
