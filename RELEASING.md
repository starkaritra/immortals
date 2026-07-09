# Releasing the engine

The engine ships as a **standalone `immortals-engine` binary** (PyInstaller) so end users — and the
desktop product [Immortals Console](https://github.com/starkaritra/immortals-console) — need **no
Python**. This is the upstream half of a two-repo release; the Console pins and bundles the binary
you produce here (see the Console's `RELEASING.md`).

```
┌────────────────────────────┐        pinned by the Console's .engine-version
│  immortals (this repo)     │  ─────────────────────────────────────────────▶  immortals-console
│  PyInstaller → per-OS binary,  attached to this repo's GitHub Release          bundles it at its
└────────────────────────────┘                                                    own release time
```

## What CI produces
On a `v*` tag (or a manual run), `.github/workflows/release.yml` builds one archive per OS and
attaches all three to the GitHub Release. **These asset names are a contract** the Console's download
step depends on — don't rename them without updating the Console too:

| OS | Asset |
|---|---|
| Windows | `immortals-engine-windows-x64.zip` |
| macOS | `immortals-engine-macos-arm64.tar.gz` |
| Linux | `immortals-engine-linux-x64.tar.gz` |

Each archive contains the PyInstaller **onedir** output (`immortals-engine/` — the executable plus
its `_internal/` payload with the bundled `registry/`, `agents/`, `skills/`).

## Cut a release
1. Bump the version (single source of truth): `immortals.__version__` (read by `pyproject.toml`).
   Update `CHANGELOG.md` (move `Unreleased` → the new version).
2. Tag and push:
   ```bash
   git tag v0.1.0 && git push origin v0.1.0
   ```
   The **Release engine** workflow builds + attaches the three binaries.

> **GitHub Desktop gotcha:** pushing a commit and a tag together can drop the tag event, so the
> tag-triggered build won't fire, and publishing a release from an *already-existing* tag triggers
> nothing. If that happens, use the manual trigger below.

## Manual trigger (no new tag needed)
`release.yml` also has a `workflow_dispatch` — **Actions → “Release engine” → Run workflow**, enter
the existing tag (default `v0.1.0`). It checks out that tag, builds, and attaches the binaries to its
release. Same button exists on the Console's release workflow.

## Build locally (dry run)
```pwsh
pip install -e ".[dashboard]" pyinstaller
pyinstaller packaging/immortals-engine.spec --noconfirm
# smoke test the frozen binary:
packaging/dist/immortals-engine/immortals-engine agents
```
To hand it to the Console locally: copy `packaging/dist/immortals-engine/*` into the Console's
`desktop/engine/`, then build the desktop app there (`cd desktop && npm run dist`).

## CI on every push/PR
`.github/workflows/ci.yml` runs `pip install -e ".[dev,dashboard]" && pytest` on `{ubuntu, windows}`.

## Notes
- Providers are **SDK-free (raw HTTP)**, so the bundle needs only `jsonschema` + `fastapi`/`uvicorn`.
- The binary is **unsigned** by default (users may see an OS warning). Add signing later if needed.
- Release the engine **before** the Console — the Console's release downloads these assets.
