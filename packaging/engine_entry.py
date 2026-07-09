"""PyInstaller entry point for the packaged engine (production sidecar).

The desktop app spawns this frozen binary instead of ``python -m immortals``. It points the engine
at the assets bundled inside the PyInstaller payload (``registry/``, ``agents/``, ``skills/`` +
package data) by defaulting ``IMMORTALS_HOME`` to the bundle root, then hands off to the normal CLI
(so ``immortals-engine dashboard --db … --create --port …`` works exactly like the CLI).
"""

import os
import sys


def _bundle_root() -> str:
    # PyInstaller onedir/onefile exposes the extracted payload dir as sys._MEIPASS.
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))


os.environ.setdefault("IMMORTALS_HOME", _bundle_root())

from immortals.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main() or 0)
