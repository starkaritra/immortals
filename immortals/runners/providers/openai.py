"""OpenAI adapter — Chat Completions with tool-calling (AS-030).

Translation helpers are pure and unit-tested without the SDK or a key.
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
    post_json,
)


def _to_wire_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    return [{"type": "function",
             "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}}
            for t in tools]


def _to_wire_messages(system: str, messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
    wire: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in messages:
        if m.role == "tool":
            wire.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
        elif m.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": m.content or None}
            if m.tool_calls:
                entry["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                    for tc in m.tool_calls
                ]
            wire.append(entry)
        else:
            wire.append({"role": "user", "content": m.content})
    return wire


def _parse_response(payload: dict[str, Any]) -> ProviderResponse:
    choice = (payload.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    tool_calls: list[ToolCall] = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        raw = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except json.JSONDecodeError:
            args = {"_raw": raw}
        tool_calls.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args))
    usage = payload.get("usage") or {}
    return ProviderResponse(
        text=msg.get("content") or "",
        tool_calls=tool_calls,
        model=payload.get("model", ""),
        usage=Usage(int(usage.get("prompt_tokens", 0) or 0), int(usage.get("completion_tokens", 0) or 0)),
        stop_reason=choice.get("finish_reason", "") or "",
    )


class OpenAIProvider(ModelProvider):
    """OpenAI via the official ``openai`` SDK. Key: ``OPENAI_API_KEY`` (``OPENAI_BASE_URL`` optional)."""

    name = "openai"
    default_model = "gpt-4o"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")

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
        if not self._api_key:
            raise ProviderError("OPENAI_API_KEY is not set")
        body: dict[str, Any] = {
            "model": model or self.default_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": _to_wire_messages(system, messages),
        }
        if tools:
            body["tools"] = _to_wire_tools(tools)
        payload = post_json(self._base_url + "/chat/completions", body,
                            {"Authorization": f"Bearer {self._api_key}"})
        resp = _parse_response(payload)
        if on_text and resp.text:
            on_text(resp.text)
        return resp
