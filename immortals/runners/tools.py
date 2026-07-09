"""A minimal, workspace-confined tool harness for :class:`ApiRunner` (AS-030).

The direct-API runner drives the tool loop itself, so it needs a set of tools the model can call.
This harness ships the small, high-value set — ``read_file``, ``write_file``, ``run_shell``,
``search`` — with two safety properties baked in:

- **Workspace confinement:** every path resolves *inside* a single ``workspace`` root; a path that
  escapes it (``..`` traversal, absolute paths elsewhere) is refused. Untrusted model output is
  never allowed to read or write arbitrary disk locations.
- **Approval gate:** mutating/side-effecting tools (``write_file``, ``run_shell``) are only executed
  if an ``approve(action, detail) -> bool`` callback allows it. The default policy **denies** them,
  so a harness is read-only unless the caller opts into writes (matching the engine's
  least-privilege guardrail philosophy; the GUI later wires this to a human approval prompt).

Tool errors are returned as strings (the runner feeds them back to the model), never raised.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

from .providers import ToolSpec

# (action, human-readable detail) -> allowed?  Default policy denies side effects.
ApprovalFn = Callable[[str, str], bool]


def _deny(action: str, detail: str) -> bool:
    return False


class ToolError(RuntimeError):
    """A tool could not run (bad path, denied approval, process failure)."""


class ToolHarness:
    """Read/write/shell/search tools confined to one workspace, gated by an approval callback."""

    def __init__(
        self,
        workspace: str | Path,
        *,
        approve: ApprovalFn | None = None,
        shell_timeout_s: int = 120,
        max_read_bytes: int = 200_000,
    ):
        self.root = Path(workspace).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.approve = approve or _deny
        self.shell_timeout_s = shell_timeout_s
        self.max_read_bytes = max_read_bytes

    # -- path safety -------------------------------------------------------------------

    def _resolve(self, rel: str) -> Path:
        """Resolve ``rel`` inside the workspace, refusing anything that escapes it."""
        if not rel or not isinstance(rel, str):
            raise ToolError("path must be a non-empty string")
        candidate = (self.root / rel).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ToolError(f"path {rel!r} escapes the workspace")
        return candidate

    # -- tool schema -------------------------------------------------------------------

    def specs(self) -> list[ToolSpec]:
        s = lambda **p: {"type": "object", "properties": p, "required": list(p)}  # noqa: E731
        return [
            ToolSpec("read_file", "Read a UTF-8 text file inside the workspace.",
                     s(path={"type": "string", "description": "workspace-relative path"})),
            ToolSpec("write_file", "Create or overwrite a text file inside the workspace.",
                     s(path={"type": "string"}, content={"type": "string"})),
            ToolSpec("run_shell", "Run a shell command in the workspace and return its output.",
                     s(command={"type": "string"})),
            ToolSpec("search", "Case-insensitive substring search across workspace files.",
                     s(query={"type": "string"})),
        ]

    # -- dispatch ----------------------------------------------------------------------

    def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        handler = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "run_shell": self._run_shell,
            "search": self._search,
        }.get(name)
        if handler is None:
            raise ToolError(f"unknown tool {name!r}")
        return handler(arguments or {})

    def _read_file(self, args: dict[str, Any]) -> str:
        path = self._resolve(args.get("path", ""))
        if not path.is_file():
            raise ToolError(f"not a file: {args.get('path')!r}")
        data = path.read_bytes()[: self.max_read_bytes]
        return data.decode("utf-8", errors="replace")

    def _write_file(self, args: dict[str, Any]) -> str:
        rel = args.get("path", "")
        path = self._resolve(rel)
        content = args.get("content", "")
        if not self.approve("write_file", f"{rel} ({len(content)} chars)"):
            raise ToolError(f"write to {rel!r} was not approved")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} chars to {rel}"

    def _run_shell(self, args: dict[str, Any]) -> str:
        command = args.get("command", "")
        if not command:
            raise ToolError("command must be a non-empty string")
        if not self.approve("run_shell", command):
            raise ToolError(f"shell command was not approved: {command!r}")
        try:
            proc = subprocess.run(
                command, shell=True, cwd=str(self.root), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=self.shell_timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolError(f"command timed out after {self.shell_timeout_s}s") from exc
        out = (proc.stdout or "")[-8000:]
        err = (proc.stderr or "")[-2000:]
        return f"exit={proc.returncode}\n--- stdout ---\n{out}\n--- stderr ---\n{err}".strip()

    def _search(self, args: dict[str, Any]) -> str:
        query = (args.get("query") or "").lower()
        if not query:
            raise ToolError("query must be a non-empty string")
        hits: list[str] = []
        for p in self.root.rglob("*"):
            if not p.is_file():
                continue
            try:
                for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if query in line.lower():
                        hits.append(f"{p.relative_to(self.root)}:{i}: {line.strip()[:200]}")
                        if len(hits) >= 100:
                            return "\n".join(hits) + "\n… (truncated at 100 hits)"
            except OSError:
                continue
        return "\n".join(hits) if hits else "no matches"
