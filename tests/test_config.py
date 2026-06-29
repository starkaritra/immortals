"""Tests for the env-overridable config layer + persona bundling/install (decision AS-024)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from immortals import config
from immortals.cli import main
from immortals.registry import Registry
from immortals.runners import CopilotRunner

REPO_ROOT = Path(__file__).resolve().parents[1]


# -- config defaults & overrides -----------------------------------------------------------

def test_defaults_resolve_to_repo_assets(monkeypatch):
    for var in ("IMMORTALS_HOME", "IMMORTALS_REGISTRY_DIR", "IMMORTALS_AGENTS_DIR"):
        monkeypatch.delenv(var, raising=False)
    assert config.registry_dir() == REPO_ROOT / "registry"
    assert config.agents_dir() == REPO_ROOT / "agents"


def test_home_override_repoints_assets(monkeypatch, tmp_path):
    monkeypatch.setenv("IMMORTALS_HOME", str(tmp_path))
    monkeypatch.delenv("IMMORTALS_REGISTRY_DIR", raising=False)
    monkeypatch.delenv("IMMORTALS_AGENTS_DIR", raising=False)
    assert config.registry_dir() == tmp_path / "registry"
    assert config.agents_dir() == tmp_path / "agents"


def test_explicit_dir_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("IMMORTALS_REGISTRY_DIR", str(tmp_path / "r"))
    assert config.registry_dir() == tmp_path / "r"


def test_copilot_bin_override(monkeypatch):
    monkeypatch.setenv("IMMORTALS_COPILOT_BIN", "/opt/copilot")
    assert config.copilot_bin() == "/opt/copilot"


def test_copilot_paths_override(monkeypatch, tmp_path):
    monkeypatch.setenv("COPILOT_AGENTS_DIR", str(tmp_path / "ag"))
    monkeypatch.setenv("IMMORTALS_MCP_CONFIG", str(tmp_path / "cfg.json"))
    assert config.copilot_agents_dir() == tmp_path / "ag"
    assert config.copilot_mcp_config_path() == tmp_path / "cfg.json"


# -- no hard-coded personal paths remain ---------------------------------------------------

def test_no_hardcoded_personal_paths_in_package():
    offenders = []
    for py in (REPO_ROOT / "immortals").rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "C:\\Code" in text or "t-aritradas" in text:
            offenders.append(py.name)
    assert offenders == []


def test_bundled_managerAS_persona_is_path_agnostic():
    md = (REPO_ROOT / "agents" / "managerAS.md").read_text(encoding="utf-8")
    assert "C:\\Code\\Immortals" not in md
    assert ".venv\\Scripts" not in md


# -- registry resolves through config ------------------------------------------------------

def test_registry_loads_via_config_default(monkeypatch):
    monkeypatch.delenv("IMMORTALS_HOME", raising=False)
    monkeypatch.delenv("IMMORTALS_REGISTRY_DIR", raising=False)
    reg = Registry.load()
    assert "coderAS" in reg and "researchAS" in reg


def test_registry_honors_registry_dir_env(monkeypatch, tmp_path):
    (tmp_path / "soloAS.json").write_text(json.dumps({
        "schema": "registry/v1", "agent": "soloAS", "summary": "x",
        "capabilities": ["demo"],
    }), encoding="utf-8")
    monkeypatch.setenv("IMMORTALS_REGISTRY_DIR", str(tmp_path))
    reg = Registry.load()
    assert reg.agents() == ["soloAS"]


# -- copilot runner uses configured binary -------------------------------------------------

def test_runner_defaults_to_config_bin(monkeypatch):
    monkeypatch.setenv("IMMORTALS_COPILOT_BIN", "copilot-custom")
    assert CopilotRunner().executable == "copilot-custom"


def test_runner_explicit_executable_wins(monkeypatch):
    monkeypatch.setenv("IMMORTALS_COPILOT_BIN", "ignored")
    assert CopilotRunner(executable="explicit").executable == "explicit"


# -- agents install ------------------------------------------------------------------------

def test_agents_install_copies_bundled_personas(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("IMMORTALS_AGENTS_DIR", raising=False)
    dest = tmp_path / "copilot_agents"
    rc = main(["agents", "install", "--dest", str(dest)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["status"] == "ok"
    assert "managerAS.md" in out["installed"]
    assert (dest / "managerAS.md").exists()


def test_agents_install_is_idempotent(tmp_path, capsys):
    dest = tmp_path / "copilot_agents"
    main(["agents", "install", "--dest", str(dest)])
    capsys.readouterr()
    main(["agents", "install", "--dest", str(dest)])
    out = json.loads(capsys.readouterr().out)
    assert out["installed"] == [] and "managerAS.md" in out["skipped"]


def test_agents_install_force_overwrites(tmp_path, capsys):
    dest = tmp_path / "copilot_agents"
    main(["agents", "install", "--dest", str(dest)])
    (dest / "managerAS.md").write_text("EDITED", encoding="utf-8")
    capsys.readouterr()
    main(["agents", "install", "--dest", str(dest), "--force"])
    out = json.loads(capsys.readouterr().out)
    assert "managerAS.md" in out["installed"]
    assert (dest / "managerAS.md").read_text(encoding="utf-8") != "EDITED"


def test_agents_list_still_works(capsys):
    rc = main(["agents"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and any(a["agent"] == "coderAS" for a in out["agents"])
