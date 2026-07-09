"""PyInstaller spec for the Immortals engine sidecar (onedir).

Build:  pyinstaller packaging/immortals-engine.spec --noconfirm
Output: dist/immortals-engine/immortals-engine(.exe) + its _internal payload.

The desktop app ships this whole ``dist/immortals-engine`` folder and spawns the binary. Providers
are SDK-free (HTTP), so the only third-party deps are jsonschema + fastapi/uvicorn.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules
import os

HERE = SPECPATH
ROOT = os.path.dirname(HERE)

datas = []
binaries = []
hiddenimports = []

# The engine package (with its contracts/schemas + dashboard/static package data) and the runtime
# deps that use dynamic imports.
for pkg in ("immortals", "fastapi", "starlette", "uvicorn", "jsonschema", "jsonschema_specifications",
            "anyio", "sniffio", "click", "h11", "certifi"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# uvicorn resolves its protocol/loop/lifespan implementations dynamically.
hiddenimports += collect_submodules("uvicorn")

# Repo-root assets the engine reads via IMMORTALS_HOME (registry manifests, personas, skills).
datas += [
    (os.path.join(ROOT, "registry"), "registry"),
    (os.path.join(ROOT, "agents"), "agents"),
    (os.path.join(ROOT, "skills"), "skills"),
]

a = Analysis(
    [os.path.join(HERE, "engine_entry.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],  # only used by the projects folder-picker (dev/CLI), not the sidecar
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="immortals-engine",
          console=True, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="immortals-engine")
