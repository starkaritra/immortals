"""Capability registry: load and query the agent manifests in the top-level ``registry/``."""

from .loader import Registry, AgentManifest

__all__ = ["Registry", "AgentManifest"]
