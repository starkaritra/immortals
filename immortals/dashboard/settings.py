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
import shutil
import stat
import urllib.request
from pathlib import Path
from typing import Any

from immortals import config
from immortals.runners.providers import ModelProvider, get_provider

from fastapi import Body, HTTPException
from fastapi.responses import StreamingResponse

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

# One-click local models (pulled via Ollama, which downloads + serves GGUF from its registry or
# directly from Hugging Face via `hf.co/<user>/<repo>`).
SUGGESTED_LOCAL: list[dict[str, Any]] = [
    {"name": "qwen2.5:7b", "label": "Qwen2.5 7B", "size": "~4.7 GB", "note": "best small all-rounder + tools"},
    {"name": "qwen2.5:3b", "label": "Qwen2.5 3B", "size": "~1.9 GB", "note": "efficient, decent tools"},
    {"name": "qwen2.5:1.5b", "label": "Qwen2.5 1.5B", "size": "~1.0 GB", "note": "very light"},
    {"name": "qwen2.5-coder:7b", "label": "Qwen2.5-Coder 7B", "size": "~4.7 GB", "note": "top small coder"},
    {"name": "qwen2.5-coder:1.5b", "label": "Qwen2.5-Coder 1.5B", "size": "~1.0 GB", "note": "light coder"},
    {"name": "llama3.1:8b", "label": "Llama 3.1 8B", "size": "~4.9 GB", "note": "strong general + tools"},
    {"name": "llama3.2:3b", "label": "Llama 3.2 3B", "size": "~2.0 GB", "note": "efficient general"},
    {"name": "llama3.2:1b", "label": "Llama 3.2 1B", "size": "~1.3 GB", "note": "tiny / edge"},
    {"name": "gemma2:9b", "label": "Gemma 2 9B", "size": "~5.4 GB", "note": "Google, strong"},
    {"name": "gemma2:2b", "label": "Gemma 2 2B", "size": "~1.6 GB", "note": "tiny, high quality"},
    {"name": "phi3.5", "label": "Phi-3.5-mini 3.8B", "size": "~2.2 GB", "note": "reasoning-dense, fast"},
    {"name": "phi4", "label": "Phi-4 14B", "size": "~9.1 GB", "note": "punches up, reasoning"},
    {"name": "glm4:9b", "label": "GLM-4 9B", "size": "~5.5 GB", "note": "multilingual + tools"},
    {"name": "mistral-nemo", "label": "Mistral-Nemo 12B", "size": "~7.1 GB", "note": "long context + tools"},
    {"name": "deepseek-r1:7b", "label": "DeepSeek-R1 7B", "size": "~4.7 GB", "note": "reasoning (distill)"},
    {"name": "deepseek-r1:1.5b", "label": "DeepSeek-R1 1.5B", "size": "~1.1 GB", "note": "tiny reasoning"},
    {"name": "granite3.1-dense:8b", "label": "Granite 3.1 8B", "size": "~4.9 GB", "note": "IBM, tools / RAG"},
    {"name": "smollm2:1.7b", "label": "SmolLM2 1.7B", "size": "~1.8 GB", "note": "ultra-light chat"},
]


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


def _provider_from_cfg(cfg: dict[str, Any], store: "SettingsStore | None" = None) -> tuple[ModelProvider, str | None]:
    """Build a provider from an explicit config dict (used by the Test button — tests what's on
    screen). If ``api_key`` is empty but an ``id`` is given, reuse the stored key for that id."""
    adapter = cfg.get("adapter")
    if adapter not in _ADAPTERS:
        raise ValueError(f"adapter must be one of {sorted(_ADAPTERS)}")
    api_key = cfg.get("api_key")
    if not api_key and store is not None and cfg.get("id"):
        existing = store.get(cfg["id"])
        api_key = existing.get("api_key") if existing else None
    kwargs: dict[str, Any] = {}
    if api_key:
        kwargs["api_key"] = api_key
    base = cfg.get("base_url")
    if base and adapter == "openai":
        kwargs["base_url"] = base
    elif base and adapter == "ollama":
        kwargs["host"] = base
    return get_provider(adapter, **kwargs), cfg.get("model")


def test_config(cfg: dict[str, Any], store: "SettingsStore | None" = None) -> dict[str, Any]:
    """Make a tiny live call to validate a provider config's key/endpoint. Never raises."""
    import time

    from immortals.runners.providers import ChatMessage

    try:
        provider, model = _provider_from_cfg(cfg, store)
    except Exception as exc:  # noqa: BLE001 - surface as a result, not a 500
        return {"ok": False, "error": str(exc)}
    started = time.monotonic()
    try:
        resp = provider.complete(
            system="You are a connectivity health check.",
            messages=[ChatMessage(role="user", content="Reply with the single word: ok")],
            model=model, temperature=0.0, max_tokens=5,
        )
    except Exception as exc:  # noqa: BLE001 - missing key/SDK, HTTP/network, bad endpoint
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True, "model": resp.model or model or provider.default_model,
        "latency_ms": round((time.monotonic() - started) * 1000),
        "sample": (resp.text or "").strip()[:80],
    }


# -- Ollama: one-click local model download + status ------------------------------------

def _ollama_host() -> str:
    return (os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")


def ollama_status() -> dict[str, Any]:
    """Whether the Ollama binary is installed and its server is reachable, + installed models."""
    host = _ollama_host()
    installed = shutil.which("ollama") is not None
    models: list[str] = []
    running = False
    try:
        with urllib.request.urlopen(host + "/api/tags", timeout=2) as r:
            models = [m.get("name") for m in json.load(r).get("models", [])]
            running = True
    except Exception:  # noqa: BLE001 - not running / not installed
        pass
    return {"installed": installed, "running": running, "host": host, "models": models}


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

    @app.post("/api/settings/providers/test")
    def test_endpoint(body: dict = Body(...)) -> dict[str, Any]:
        return test_config(body, store)

    @app.get("/api/settings/ollama/status")
    def ollama_status_ep() -> dict[str, Any]:
        return ollama_status()

    @app.get("/api/settings/ollama/recommended")
    def ollama_recommended() -> dict[str, Any]:
        return {"models": SUGGESTED_LOCAL, "status": ollama_status()}

    @app.post("/api/settings/ollama/pull")
    def ollama_pull(body: dict = Body(...)):
        """Stream `ollama pull` progress (NDJSON) by proxying Ollama's /api/pull."""
        model = (body.get("model") or "").strip()
        if not model:
            raise HTTPException(status_code=422, detail="'model' is required")
        host = _ollama_host()

        def gen():
            try:
                req = urllib.request.Request(
                    host + "/api/pull",
                    data=json.dumps({"name": model, "stream": True}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req) as r:
                    for line in r:
                        yield line
            except Exception as exc:  # noqa: BLE001 - ollama not running / model not found
                yield (json.dumps({"status": "error", "error": str(exc)}) + "\n").encode()

        return StreamingResponse(gen(), media_type="application/x-ndjson")
