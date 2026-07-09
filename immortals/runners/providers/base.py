"""Normalized model-provider interface for the direct-API runner (AS-030, CON-005/007).

The engine's original worker backend (:class:`~immortals.runners.copilot_backend.CopilotRunner`)
shells out to the ``copilot`` CLI, which couples the whole suite to Copilot. To make Immortals a
**standalone** product (bring-your-own API key or a local Ollama), :class:`ApiRunner` talks to
model providers directly. This module is the seam that keeps *provider-specific* wire formats out
of the runner: the runner speaks these **normalized** types, and each adapter
(:mod:`.anthropic`, :mod:`.openai`, :mod:`.gemini`, :mod:`.ollama`) translates them to and from
its own API shape.

Nothing here imports a provider SDK — adapters lazy-import their SDK so installing one provider's
extra never forces the others. Keys are read from the environment by the adapters; never pass or
log a raw key through these types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

# A streaming sink: called with each incremental text delta as it arrives (best-effort; adapters
# that don't stream simply never call it). Kept out of the data types so responses stay picklable.
TextStream = Callable[[str], None]


class ProviderError(RuntimeError):
    """A provider adapter could not produce a response (missing SDK/key, HTTP/parse failure)."""


@dataclass
class ToolSpec:
    """A tool the model may call, in a provider-agnostic shape.

    ``input_schema`` is a JSON-Schema object describing the tool's parameters (the lingua franca
    all four providers accept, after per-adapter reshaping).
    """

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})


@dataclass
class ToolCall:
    """A model's request to invoke a tool. ``id`` correlates the call with its result message."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatMessage:
    """One turn in the conversation.

    - ``role`` is ``"user"``, ``"assistant"`` or ``"tool"``.
    - assistant turns may carry ``tool_calls``; ``content`` is the assistant's text (may be empty).
    - tool-result turns set ``role="tool"``, ``tool_call_id`` to the originating call, and put the
      result string in ``content``.
    """

    role: str
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None


@dataclass
class Usage:
    """Token accounting from a single provider call (0 when the provider doesn't report it)."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens)


@dataclass
class ProviderResponse:
    """The normalized result of one ``complete`` call."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    usage: Usage = field(default_factory=Usage)
    stop_reason: str = ""


class ModelProvider(ABC):
    """Translate a normalized chat/tool request to one provider's API and back.

    Implementations MUST:
    - lazy-import their SDK inside ``complete`` (or a helper), raising :class:`ProviderError` with a
      clear "pip install …" message when the optional extra is absent;
    - read credentials from the environment, never from arguments logged by the caller;
    - return a :class:`ProviderResponse` — surfacing tool-call requests as :class:`ToolCall` so the
      runner drives the tool loop uniformly across providers.
    """

    #: Stable short id used by ``get_provider`` and the CLI ``--provider`` flag.
    name: str = "abstract"
    #: Provider's default model when the caller doesn't pin one.
    default_model: str = ""

    @abstractmethod
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
    ) -> ProviderResponse:  # pragma: no cover - interface
        raise NotImplementedError


def _require(module: str, extra: str):
    """Import an optional provider SDK, or raise a clear install hint. Returns the module."""
    import importlib

    try:
        return importlib.import_module(module)
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised via adapters
        raise ProviderError(
            f"the {extra!r} provider needs the {module!r} package; install it with "
            f'`pip install "immortals[{extra}]"`'
        ) from exc
