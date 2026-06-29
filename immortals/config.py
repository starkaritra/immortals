"""Centralized, environment-overridable configuration (decision AS-024).

Every filesystem location Immortals touches resolves through this module so nothing is hard-coded
to a particular machine, user, or checkout path — a prerequisite for shipping the project. Defaults
are derived from the installed location; each is overridable by an environment variable so the same
build runs unchanged in a dev checkout, a packaged install, or CI.

| Setting | Env var | Default |
|---|---|---|
| Project home (root of bundled assets) | ``IMMORTALS_HOME`` | the repo root (parent of this package) |
| Registry manifest dir | ``IMMORTALS_REGISTRY_DIR`` | ``<home>/registry`` |
| Bundled agent personas dir | ``IMMORTALS_AGENTS_DIR`` | ``<home>/agents`` |
| ``copilot`` executable | ``IMMORTALS_COPILOT_BIN`` | ``copilot`` (resolved on ``PATH``) |
| Copilot persona lookup dir | ``COPILOT_AGENTS_DIR`` | ``~/.copilot/agents`` |
| Copilot MCP config file | ``IMMORTALS_MCP_CONFIG`` | ``~/.copilot/mcp-config.json`` |
"""

from __future__ import annotations

import os
from pathlib import Path

# The installed package dir (…/immortals) and the project root that ships its sibling assets
# (``registry/``, ``agents/``). For a source checkout the root is the repo; for a packaged install
# set ``IMMORTALS_HOME`` to wherever the assets were placed.
_PACKAGE_DIR = Path(__file__).resolve().parent
_DEFAULT_HOME = _PACKAGE_DIR.parent


def home() -> Path:
    """Root holding the bundled assets (``registry/``, ``agents/``). Override: ``IMMORTALS_HOME``."""
    env = os.environ.get("IMMORTALS_HOME")
    return Path(env).expanduser() if env else _DEFAULT_HOME


def registry_dir() -> Path:
    """Directory of ``registry/v1`` manifests. Override: ``IMMORTALS_REGISTRY_DIR``."""
    env = os.environ.get("IMMORTALS_REGISTRY_DIR")
    return Path(env).expanduser() if env else home() / "registry"


def agents_dir() -> Path:
    """Directory of the bundled persona ``.md`` files. Override: ``IMMORTALS_AGENTS_DIR``."""
    env = os.environ.get("IMMORTALS_AGENTS_DIR")
    return Path(env).expanduser() if env else home() / "agents"


def copilot_bin() -> str:
    """The ``copilot`` executable name/path. Override: ``IMMORTALS_COPILOT_BIN``."""
    return os.environ.get("IMMORTALS_COPILOT_BIN", "copilot")


def copilot_agents_dir() -> Path:
    """Where the copilot CLI resolves ``--agent`` personas. Override: ``COPILOT_AGENTS_DIR``."""
    env = os.environ.get("COPILOT_AGENTS_DIR")
    return Path(env).expanduser() if env else Path.home() / ".copilot" / "agents"


def copilot_mcp_config_path() -> Path:
    """The copilot MCP config file. Override: ``IMMORTALS_MCP_CONFIG``."""
    env = os.environ.get("IMMORTALS_MCP_CONFIG")
    return Path(env).expanduser() if env else Path.home() / ".copilot" / "mcp-config.json"
