"""Tests for the capability registry loader."""

from __future__ import annotations

import json

import pytest

from agentsuite.registry import Registry, AgentManifest
from agentsuite.contracts import ContractError


def test_loads_real_registry():
    reg = Registry.load()
    agents = reg.agents()
    # The worker agents we authored manifests for.
    for expected in ["coderAS", "experimentAS", "teachAS", "researchAS", "discussAS"]:
        assert expected in agents
        assert expected in reg


def test_get_unknown_raises():
    reg = Registry.load()
    with pytest.raises(KeyError):
        reg.get("nopeAS")


def test_capability_lookup():
    reg = Registry.load()
    designers = [m.agent for m in reg.with_capability("experiment_design")]
    assert "experimentAS" in designers


def test_manifest_validates_schema():
    with pytest.raises(ContractError):
        AgentManifest.from_dict({"schema": "registry/v1", "agent": "x", "summary": "y"})  # no capabilities


def test_load_from_custom_dir(tmp_path):
    (tmp_path / "fooAS.json").write_text(
        json.dumps({
            "schema": "registry/v1",
            "agent": "fooAS",
            "summary": "does foo",
            "capabilities": ["foo"],
        }),
        encoding="utf-8",
    )
    reg = Registry.load(tmp_path)
    assert reg.agents() == ["fooAS"]
    assert reg.get("fooAS").capabilities == ("foo",)
