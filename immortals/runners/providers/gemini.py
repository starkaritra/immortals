"""Google Gemini adapter — ``google-genai`` SDK, ``generateContent`` with function calling (AS-030).

Gemini has no dedicated "tool" role: a model's request is a ``functionCall`` part on a ``model``
turn, and a tool result is a ``functionResponse`` part on a ``user`` turn. The pure helpers below
do that reshaping and are unit-tested without the SDK or a key.
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
    post_json,
)


def _to_wire_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    """One tool object holding all function declarations (Gemini's expected shape)."""
    return [{"function_declarations": [
        {"name": t.name, "description": t.description, "parameters": t.input_schema} for t in tools
    ]}]


def _to_wire_contents(messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "tool":
            contents.append({"role": "user", "parts": [
                {"function_response": {"name": m.tool_call_id or "tool",
                                       "response": {"result": m.content}}}
            ]})
        elif m.role == "assistant":
            parts: list[dict[str, Any]] = []
            if m.content:
                parts.append({"text": m.content})
            for tc in m.tool_calls:
                parts.append({"function_call": {"name": tc.name, "args": tc.arguments}})
            contents.append({"role": "model", "parts": parts or [{"text": ""}]})
        else:
            contents.append({"role": "user", "parts": [{"text": m.content}]})
    return contents


def _parse_response(payload: dict[str, Any]) -> ProviderResponse:
    candidate = (payload.get("candidates") or [{}])[0]
    parts = ((candidate.get("content") or {}).get("parts")) or []
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for i, part in enumerate(parts):
        if "text" in part and part["text"]:
            text_parts.append(part["text"])
        fc = part.get("function_call") or part.get("functionCall")
        if fc:
            name = fc.get("name", "")
            # Gemini gives no call id; synthesize a stable one so tool results can be correlated.
            tool_calls.append(ToolCall(id=f"{name}-{i}", name=name,
                                       arguments=fc.get("args") or fc.get("arguments") or {}))
    meta = payload.get("usage_metadata") or payload.get("usageMetadata") or {}
    in_tok = meta.get("prompt_token_count", meta.get("promptTokenCount", 0)) or 0
    out_tok = meta.get("candidates_token_count", meta.get("candidatesTokenCount", 0)) or 0
    return ProviderResponse(
        text="".join(text_parts),
        tool_calls=tool_calls,
        model=payload.get("model_version", payload.get("modelVersion", "")) or "",
        usage=Usage(int(in_tok), int(out_tok)),
        stop_reason=candidate.get("finish_reason", candidate.get("finishReason", "")) or "",
    )


class GeminiProvider(ModelProvider):
    """Gemini via the ``google-genai`` SDK. Key: ``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``)."""

    name = "gemini"
    default_model = "gemini-2.5-flash"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self._base_url = (base_url or "https://generativelanguage.googleapis.com").rstrip("/")

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
            raise ProviderError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")
        mdl = model or self.default_model
        body: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": _to_wire_contents(messages),
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if tools:
            body["tools"] = _to_wire_tools(tools)
        url = f"{self._base_url}/v1beta/models/{mdl}:generateContent?key={self._api_key}"
        payload = post_json(url, body, {})
        resp = _parse_response(payload)
        if not resp.model:
            resp.model = mdl
        if on_text and resp.text:
            on_text(resp.text)
        return resp
