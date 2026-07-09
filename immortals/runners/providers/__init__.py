"""Model-provider adapters behind one normalized interface (AS-030, CON-005).

All four wrappers ship so the standalone runner is provider-agnostic from day one; the active one
is chosen by name (CLI ``--provider`` / ``get_provider``). Adapter modules lazy-import their SDK,
so importing this package never requires any provider package to be installed.
"""

from __future__ import annotations

from .base import (
    ChatMessage,
    ModelProvider,
    ProviderError,
    ProviderResponse,
    TextStream,
    ToolCall,
    ToolSpec,
    Usage,
)
from .fake import FakeProvider

__all__ = [
    "ChatMessage",
    "ModelProvider",
    "ProviderError",
    "ProviderResponse",
    "TextStream",
    "ToolCall",
    "ToolSpec",
    "Usage",
    "FakeProvider",
    "get_provider",
    "PROVIDER_NAMES",
]

# Name -> "module:class" (lazy: the SDK-touching modules import only when the provider is built).
_REGISTRY: dict[str, str] = {
    "anthropic": "immortals.runners.providers.anthropic:AnthropicProvider",
    "openai": "immortals.runners.providers.openai:OpenAIProvider",
    "gemini": "immortals.runners.providers.gemini:GeminiProvider",
    "ollama": "immortals.runners.providers.ollama:OllamaProvider",
    "fake": "immortals.runners.providers.fake:FakeProvider",
}

#: Selectable provider names (``fake`` is test-only but harmless to expose).
PROVIDER_NAMES = tuple(k for k in _REGISTRY if k != "fake")


def get_provider(name: str, **kwargs) -> ModelProvider:
    """Instantiate a provider adapter by name. Raises :class:`ProviderError` for unknown names."""
    import importlib

    target = _REGISTRY.get(name)
    if target is None:
        raise ProviderError(f"unknown provider {name!r}; choose from {', '.join(sorted(_REGISTRY))}")
    module_path, cls_name = target.split(":")
    cls = getattr(importlib.import_module(module_path), cls_name)
    return cls(**kwargs)
