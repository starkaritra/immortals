"""Tests for the model-provider settings store + API (AS-035).

Settings file is redirected to a temp path via IMMORTALS_SETTINGS; keys are asserted to be masked
on read and never returned in full.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi", reason="dashboard extra not installed")
pytest.importorskip("httpx", reason="fastapi TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

from immortals.dashboard.app import create_app  # noqa: E402
from immortals.dashboard.settings import SettingsStore, build_provider  # noqa: E402
from immortals.runners.providers.openai import OpenAIProvider  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTALS_SETTINGS", str(tmp_path / "settings.json"))
    return TestClient(create_app(str(tmp_path / "run.db")))


def test_catalog_lists_suggestions(client):
    ids = {c["id"] for c in client.get("/api/settings/catalog").json()["catalog"]}
    assert {"anthropic", "openai", "groq", "openrouter", "ollama", "deepseek"}.issubset(ids)


def test_upsert_masks_key_on_read(client):
    r = client.put("/api/settings/providers", json={
        "id": "groq", "label": "Groq", "adapter": "openai",
        "base_url": "https://api.groq.com/openai/v1", "api_key": "sk-secret-1234",
        "model": "llama-3.1-8b-instant", "enabled": True,
    })
    assert r.status_code == 200
    row = r.json()
    assert row["has_key"] is True and row["key_hint"] == "…1234"
    assert "api_key" not in row  # full key never returned

    listed = client.get("/api/settings/providers").json()["providers"]
    groq = next(p for p in listed if p["id"] == "groq")
    assert groq["has_key"] is True and "api_key" not in groq
    assert groq["base_url"].endswith("/openai/v1")


def test_upsert_keeps_key_when_omitted(client):
    client.put("/api/settings/providers", json={"id": "x", "adapter": "openai", "api_key": "sk-abc9",
                                                "model": "m1", "base_url": "http://h/v1"})
    # Edit the model without resending the key.
    client.put("/api/settings/providers", json={"id": "x", "adapter": "openai", "model": "m2"})
    store = SettingsStore()  # reads via IMMORTALS_SETTINGS env
    cfg = store.get("x")
    assert cfg["api_key"] == "sk-abc9" and cfg["model"] == "m2"


def test_delete_provider(client):
    client.put("/api/settings/providers", json={"id": "gone", "adapter": "openai", "api_key": "k"})
    assert client.delete("/api/settings/providers/gone").status_code == 200
    assert all(p["id"] != "gone" for p in client.get("/api/settings/providers").json()["providers"])


def test_bad_adapter_rejected(client):
    assert client.put("/api/settings/providers", json={"id": "z", "adapter": "nope"}).status_code == 422


def test_connection_test_reports_missing_key(client):
    # anthropic provider with no key + no env key -> the test call fails gracefully (ok:false).
    import os

    os.environ.pop("ANTHROPIC_API_KEY", None)
    client.put("/api/settings/providers", json={"id": "anthropic", "adapter": "anthropic",
                                                "model": "claude-3-5-haiku-latest"})
    res = client.post("/api/settings/providers/anthropic/test").json()
    assert res["ok"] is False
    assert "ANTHROPIC_API_KEY" in res["error"]


def test_build_provider_from_config(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTALS_SETTINGS", str(tmp_path / "s.json"))
    store = SettingsStore()
    store.upsert({"id": "groq", "adapter": "openai", "base_url": "https://api.groq.com/openai/v1",
                  "api_key": "sk-1", "model": "llama-3.1-8b-instant"})
    provider, model = build_provider(store, "groq")
    assert isinstance(provider, OpenAIProvider)
    assert provider._base_url == "https://api.groq.com/openai/v1"  # custom endpoint wired
    assert model == "llama-3.1-8b-instant"


def test_build_provider_falls_back_to_adapter_name(tmp_path, monkeypatch):
    monkeypatch.setenv("IMMORTALS_SETTINGS", str(tmp_path / "s2.json"))
    provider, model = build_provider(SettingsStore(), "anthropic")
    assert provider.name == "anthropic" and model is None
