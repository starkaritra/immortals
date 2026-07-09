"""Anthropic (Claude) adapter — Messages API with tool-use (AS-030).

Translation helpers (``_to_wire_*`` / ``_parse_response``) are pure and unit-tested without the
SDK or a key; only :meth:`AnthropicProvider.complete` touches the network.
"""

from __future__ import annotations

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
    return [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools]


def _to_wire_messages(messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
    """Map normalized messages to Anthropic's content-block format.

    Assistant tool calls become ``tool_use`` blocks; ``role="tool"`` results become a ``user``
    message carrying a ``tool_result`` block keyed by ``tool_use_id``.
    """
    wire: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "tool":
            wire.append({
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}],
            })
        elif m.role == "assistant":
            blocks: list[dict[str, Any]] = []
            if m.content:
                blocks.append({"type": "text", "text": m.content})
            for tc in m.tool_calls:
                blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
            wire.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
        else:
            wire.append({"role": "user", "content": m.content})
    return wire


def _parse_response(payload: dict[str, Any]) -> ProviderResponse:
    """Fold an Anthropic Messages response (as a dict) into a :class:`ProviderResponse`."""
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in payload.get("content", []) or []:
        btype = block.get("type")
        if btype == "text":
            text_parts.append(block.get("text", ""))
        elif btype == "tool_use":
            tool_calls.append(ToolCall(id=block.get("id", ""), name=block.get("name", ""),
                                       arguments=block.get("input", {}) or {}))
    usage = payload.get("usage") or {}
    return ProviderResponse(
        text="".join(text_parts),
        tool_calls=tool_calls,
        model=payload.get("model", ""),
        usage=Usage(int(usage.get("input_tokens", 0) or 0), int(usage.get("output_tokens", 0) or 0)),
        stop_reason=payload.get("stop_reason", "") or "",
    )


class AnthropicProvider(ModelProvider):
    """Claude via the official ``anthropic`` SDK. Key: ``ANTHROPIC_API_KEY``."""

    name = "anthropic"
    default_model = "claude-sonnet-4-5"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

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
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        sdk = _require("anthropic", "anthropic")
        client = sdk.Anthropic(api_key=self._api_key)
        kwargs: dict[str, Any] = {
            "model": model or self.default_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": _to_wire_messages(messages),
        }
        if tools:
            kwargs["tools"] = _to_wire_tools(tools)
        try:
            msg = client.messages.create(**kwargs)
        except Exception as exc:  # pragma: no cover - network/SDK errors
            raise ProviderError(f"anthropic call failed: {exc}") from exc
        resp = _parse_response(msg.model_dump() if hasattr(msg, "model_dump") else dict(msg))
        if on_text and resp.text:
            on_text(resp.text)
        return resp
