"""A deterministic, in-process provider for tests and dry runs (no network, no SDK, no key).

Analogous to :class:`~immortals.runners.mock.MockRunner`, but one layer down: it lets a test
*script* what the "model" returns on each successive ``complete`` call — including tool-call
requests — so the :class:`~immortals.runners.api_backend.ApiRunner` tool loop can be exercised
end to end without any provider.
"""

from __future__ import annotations

from typing import Callable, Sequence, Union

from .base import ChatMessage, ModelProvider, ProviderResponse, TextStream, ToolSpec, Usage

# A scripted turn is either a fixed response or a function of the current message list.
Turn = Union[ProviderResponse, Callable[[list[ChatMessage]], ProviderResponse]]


class FakeProvider(ModelProvider):
    """Return pre-scripted responses in order; the last one repeats once the script is exhausted."""

    name = "fake"
    default_model = "fake-1"

    def __init__(self, turns: Sequence[Turn] | None = None):
        # Default: a single plain-text answer that echoes nothing, so a no-script runner terminates.
        self._turns: list[Turn] = list(turns) if turns else [
            ProviderResponse(text="ok", model=self.default_model, usage=Usage(1, 1), stop_reason="stop")
        ]
        self._i = 0
        self.calls: list[dict] = []

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
        msgs = list(messages)
        self.calls.append({"system": system, "messages": msgs, "tools": list(tools), "model": model})
        turn = self._turns[min(self._i, len(self._turns) - 1)]
        self._i += 1
        resp = turn(msgs) if callable(turn) else turn
        if not resp.model:
            resp.model = model or self.default_model
        if on_text and resp.text:
            on_text(resp.text)
        return resp
