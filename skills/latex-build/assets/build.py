#!/usr/bin/env python3
"""Deterministic LaTeX build driver for the `latex-build` skill.

Picks an engine, runs the full bib pass, and on failure extracts the true first error from
the `.log` (the first line starting with `!`) plus its file:line context. Prefers `latexmk`
when available; otherwise runs the classic engine->bib->engine->engine sequence.

Standard library only. Requires a TeX distribution on PATH (pdflatex/xelatex/latexmk).

Usage:
  python build.py main.tex                    # auto engine, full build
  python build.py main.tex --engine xelatex
  python build.py main.tex --json
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def which(*names: str) -> str | None:
    for n in names:
        if shutil.which(n):
            return n
    return None


def detect_engine(tex: Path) -> str:
    """xelatex if the source needs system fonts / unicode-math, else pdflatex."""
    try:
        head = tex.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "pdflatex"
    if re.search(r"\\usepackage(\[[^\]]*\])?\{(fontspec|unicode-math)\}", head):
        return "xelatex"
    return "pdflatex"


def needs_biber(tex_dir: Path, stem: str) -> bool:
    for f in tex_dir.glob("*.tex"):
        try:
            if re.search(r"backend\s*=\s*biber", f.read_text(encoding="utf-8", errors="replace")):
                return True
        except OSError:
            continue
    return False


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def first_error(log_path: Path) -> str | None:
    if not log_path.exists():
        return None
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("!"):
            ctx = " | ".join(x for x in lines[i:i + 3] if x.strip())
            return ctx
    # undefined references/citations are warnings, surface them if no hard error
    for ln in lines:
        if "LaTeX Warning: Citation" in ln or "LaTeX Warning: Reference" in ln:
            return ln.strip()
    return None


def build(tex: Path, engine: str, json_out: bool) -> int:
    tex_dir = tex.parent if tex.parent != Path("") else Path(".")
    stem = tex.stem
    steps: list[dict] = []

    latexmk = which("latexmk")
    engine_bin = which(engine, "pdflatex")
    if engine_bin is None:
        msg = "no TeX engine found on PATH (install TeX Live / MiKTeX)"
        print(json.dumps({"ok": False, "error": msg}) if json_out else f"ERROR: {msg}")
        return 2

    if latexmk:
        flag = {"pdflatex": "-pdf", "xelatex": "-xelatex", "lualatex": "-lualatex"}.get(engine, "-pdf")
        cmds = [[latexmk, flag, "-interaction=nonstopmode", "-halt-on-error", tex.name]]
    else:
        base = [engine_bin, "-interaction=nonstopmode", "-halt-on-error", tex.name]
        bibtool = "biber" if needs_biber(tex_dir, stem) else "bibtex"
        bib_bin = which(bibtool) or bibtool
        cmds = [base, [bib_bin, stem], base, base]

    for cmd in cmds:
        cp = run(cmd, tex_dir)
        steps.append({"cmd": " ".join(cmd), "returncode": cp.returncode})
        # bibtex/biber returning non-zero on first pass (no .aux yet) is tolerable
        if cp.returncode != 0 and cmd[0] not in ("bibtex", "biber"):
            err = first_error(tex_dir / f"{stem}.log") or (cp.stdout or cp.stderr)[-500:]
            result = {"ok": False, "engine": engine, "steps": steps, "first_error": err}
            print(json.dumps(result, indent=2) if json_out
                  else f"BUILD FAILED ({engine})\nFirst error: {err}")
            return 1

    pdf = tex_dir / f"{stem}.pdf"
    ok = pdf.exists() and pdf.stat().st_size > 0
    result = {"ok": ok, "engine": engine, "steps": steps, "pdf": str(pdf) if ok else None}
    if json_out:
        print(json.dumps(result, indent=2))
    else:
        print(f"BUILD {'OK' if ok else 'FAILED'} ({engine}) -> {pdf if ok else 'no PDF produced'}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tex", help="path to the main .tex file")
    ap.add_argument("--engine", choices=["pdflatex", "xelatex", "lualatex"], default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    tex = Path(args.tex)
    if not tex.exists():
        print(f"ERROR: {tex} not found")
        return 2
    engine = args.engine or detect_engine(tex)
    return build(tex, engine, args.json)


if __name__ == "__main__":
    sys.exit(main())
