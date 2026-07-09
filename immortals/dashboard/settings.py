"""Model-provider settings — configure API keys / endpoints per provider (AS-035).

The Console lets users enable model providers by supplying a key (hosted) or an endpoint (local /
OpenAI-compatible). Because almost every OSS/local model server and aggregator (Ollama, LM Studio,
vLLM, Groq, OpenRouter, Together, DeepSeek, Qwen/GLM endpoints…) speaks the **OpenAI-compatible**
API, a single ``openai`` adapter + a custom ``base_url`` covers them all — so "add your own" is just
a base_url + key + model.

Secrets stay **server-side**: keys are written to ``config.settings_file()`` (under the user's home,
never the repo) and are **masked** whenever read back over the API — the browser never re-receives a
full key. Nothing here logs a key.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from immortals import config
from immortals.runners.providers import ModelProvider, get_provider

from fastapi import Body, HTTPException

# Starter catalogue the UI offers to enable. `adapter` is the wire protocol; OpenAI-compatible
# hosts all use the `openai` adapter with a fixed base_url. `local` = no key needed.
SUGGESTED: list[dict[str, Any]] = [
    {"id": "anthropic", "label": "Anthropic (Claude)", "adapter": "anthropic", "needs_key": True,
     "models": ["claude-sonnet-4-5", "claude-3-5-haiku-latest"]},
    {"id": "openai", "label": "OpenAI", "adapter": "openai", "needs_key": True,
     "models": ["gpt-4o", "gpt-4o-mini"]},
    {"id": "gemini", "label": "Google Gemini", "adapter": "gemini", "needs_key": True,
     "models": ["gemini-2.5-flash", "gemini-2.5-pro"]},
    {"id": "groq", "label": "Groq (fast OSS)", "adapter": "openai", "needs_key": True,
     "base_url": "https://api.groq.com/openai/v1",
     "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "qwen-2.5-32b"]},
    {"id": "openrouter", "label": "OpenRouter (many models)", "adapter": "openai", "needs_key": True,
     "base_url": "https://openrouter.ai/api/v1",
     "models": ["qwen/qwen-2.5-72b-instruct", "deepseek/deepseek-chat", "meta-llama/llama-3.1-8b-instruct"]},
    {"id": "together", "label": "Together AI", "adapter": "openai", "needs_key": True,
     "base_url": "https://api.together.xyz/v1",
     "models": ["Qwen/Qwen2.5-7B-Instruct-Turbo", "meta-llama/Llama-3.1-8B-Instruct-Turbo"]},
    {"id": "deepseek", "label": "DeepSeek", "adapter": "openai", "needs_key": True,
     "base_url": "https://api.deepseek.com",
     "models": ["deepseek-chat", "deepseek-coder"]},
    {"id": "ollama", "label": "Ollama (local)", "adapter": "ollama", "needs_key": False, "local": True,
     "base_url": "http://localhost:11434",
     "models": ["qwen2.5", "qwen2.5-coder", "llama3.1", "glm4", "phi3.5", "gemma2"]},
    {"id": "lmstudio", "label": "LM Studio (local)", "adapter": "openai", "needs_key": False, "local": True,
     "base_url": "http://localhost:1234/v1", "models": ["local-model"]},
    {"id": "vllm", "label": "vLLM (local)", "adapter": "openai", "needs_key": False, "local": True,
     "base_url": "http://localhost:8000/v1", "models": ["local-model"]},
]

_ADAPTERS = {"anthropic", "openai", "gemini", "ollama"}


def _mask(key: str | None) -> dict[str, Any]:
    if not key:
        return {"has_key": False, "key_hint": None}
    return {"has_key": True, "key_hint": "…" + key[-4:] if len(key) >= 4 else "…"}


class SettingsStore:
    """Persisted provider configs. A config = {id,label,adapter,base_url?,api_key?,model,enabled}."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else config.settings_file()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"providers": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"providers": []}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:  # best-effort: restrict perms (secrets live here)
            os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    def list_masked(self) -> list[dict[str, Any]]:
        out = []
        for p in self._load()["providers"]:
            row = {k: p.get(k) for k in ("id", "label", "adapter", "base_url", "model", "enabled")}
            row.update(_mask(p.get("api_key")))
            out.append(row)
        return out

    def get(self, provider_id: str) -> dict[str, Any] | None:
        for p in self._load()["providers"]:
            if p.get("id") == provider_id:
                return p
        return None

    def upsert(self, cfg: dict[str, Any]) -> dict[str, Any]:
        pid = (cfg.get("id") or "").strip()
        if not pid:
            raise HTTPException(status_code=422, detail="provider needs an 'id'")
        adapter = cfg.get("adapter")
        if adapter not in _ADAPTERS:
            raise HTTPException(status_code=422, detail=f"adapter must be one of {sorted(_ADAPTERS)}")
        data = self._load()
        existing = next((p for p in data["providers"] if p.get("id") == pid), None)
        merged = dict(existing or {})
        merged.update({
            "id": pid,
            "label": cfg.get("label", existing.get("label") if existing else pid),
            "adapter": adapter,
            "base_url": cfg.get("base_url", existing.get("base_url") if existing else None),
            "model": cfg.get("model", existing.get("model") if existing else None),
            "enabled": bool(cfg.get("enabled", existing.get("enabled", True) if existing else True)),
        })
        # Only overwrite the key if a new one was provided (empty string = keep existing).
        if cfg.get("api_key"):
            merged["api_key"] = cfg["api_key"]
        elif existing:
            merged["api_key"] = existing.get("api_key")
        if existing:
            data["providers"] = [merged if p.get("id") == pid else p for p in data["providers"]]
        else:
            data["providers"].append(merged)
        self._save(data)
        row = {k: merged.get(k) for k in ("id", "label", "adapter", "base_url", "model", "enabled")}
        row.update(_mask(merged.get("api_key")))
        return row

    def delete(self, provider_id: str) -> None:
        data = self._load()
        data["providers"] = [p for p in data["providers"] if p.get("id") != provider_id]
        self._save(data)


def build_provider(store: SettingsStore, provider_ref: str) -> tuple[ModelProvider, str | None]:
    """Resolve a configured provider id (or a bare adapter name) to a live provider + default model.

    Falls back to a bare adapter name (env-based keys) so ``provider="anthropic"`` still works
    without any stored config.
    """
    cfg = store.get(provider_ref)
    if cfg is None:
        # Bare adapter name — env keys.
        return get_provider(provider_ref if provider_ref in _ADAPTERS else "anthropic"), None
    adapter = cfg["adapter"]
    kwargs: dict[str, Any] = {}
    if cfg.get("api_key"):
        kwargs["api_key"] = cfg["api_key"]
    if cfg.get("base_url"):
        kwargs["base_url" if adapter == "openai" else "host" if adapter == "ollama" else "base_url"] = cfg["base_url"]
    # Anthropic/Gemini don't take base_url — drop it for them.
    if adapter in ("anthropic", "gemini"):
        kwargs.pop("base_url", None)
    return get_provider(adapter, **kwargs), cfg.get("model")


def attach_settings_api(app, store: SettingsStore) -> None:
    @app.get("/api/settings/catalog")
    def catalog() -> dict[str, Any]:
        return {"catalog": SUGGESTED}

    @app.get("/api/settings/providers")
    def list_providers() -> dict[str, Any]:
        return {"providers": store.list_masked()}

    @app.put("/api/settings/providers")
    def upsert_provider(body: dict = Body(...)) -> dict[str, Any]:
        return store.upsert(body)

    @app.delete("/api/settings/providers/{provider_id}")
    def delete_provider(provider_id: str) -> dict[str, Any]:
        store.delete(provider_id)
        return {"ok": True}
