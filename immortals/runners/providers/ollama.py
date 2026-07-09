"""Local Ollama adapter — the free/offline provider (AS-030).

Talks to a local Ollama server (default ``http://localhost:11434``) via the ``ollama`` SDK. No key.
Ollama's chat API supports tools; model tool-calls carry no id, so we synthesize one so results
correlate. Pure helpers are unit-tested without the SDK or a running server.
"""

from __future__ import annotations

import json
import os
from typing import Any, Sequence

from .base import (
    ChatMessage,
    ModelProvider,
    ProviderError,
    ProviderResponse,
    TextStream,
    ToolCall,
    ToolSpec,
    Usage,
    _require,
)


def _to_wire_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    return [{"type": "function",
             "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}}
            for t in tools]


def _to_wire_messages(system: str, messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
    wire: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in messages:
        if m.role == "tool":
            wire.append({"role": "tool", "content": m.content, "tool_name": m.tool_call_id or ""})
        elif m.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                entry["tool_calls"] = [
                    {"function": {"name": tc.name, "arguments": tc.arguments}} for tc in m.tool_calls
                ]
            wire.append(entry)
        else:
            wire.append({"role": "user", "content": m.content})
    return wire


def _parse_response(payload: dict[str, Any]) -> ProviderResponse:
    msg = payload.get("message") or {}
    tool_calls: list[ToolCall] = []
    for i, tc in enumerate(msg.get("tool_calls") or []):
        fn = tc.get("function") or {}
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"_raw": args}
        name = fn.get("name", "")
        tool_calls.append(ToolCall(id=f"{name}-{i}", name=name, arguments=args))
    return ProviderResponse(
        text=msg.get("content") or "",
        tool_calls=tool_calls,
        model=payload.get("model", ""),
        usage=Usage(int(payload.get("prompt_eval_count", 0) or 0), int(payload.get("eval_count", 0) or 0)),
        stop_reason=payload.get("done_reason", "") or "",
    )


class OllamaProvider(ModelProvider):
    """Local models via the ``ollama`` SDK. Host: ``OLLAMA_HOST`` (default localhost:11434)."""

    name = "ollama"
    default_model = "llama3.1"

    def __init__(self, host: str | None = None):
        self._host = host or os.environ.get("OLLAMA_HOST")

    def complete(
        self,
        *,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec] = (),
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        on_text: TextStream | None = None,
    ) -> ProviderResponse:
        sdk = _require("ollama", "ollama")
        client = sdk.Client(host=self._host) if self._host else sdk.Client()
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": _to_wire_messages(system, messages),
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if tools:
            kwargs["tools"] = _to_wire_tools(tools)
        try:
            result = client.chat(**kwargs)
        except Exception as exc:  # pragma: no cover - network/SDK errors
            raise ProviderError(f"ollama call failed: {exc}") from exc
        payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        resp = _parse_response(payload)
        if not resp.model:
            resp.model = model or self.default_model
        if on_text and resp.text:
            on_text(resp.text)
        return resp
