#!/usr/bin/env python3
"""Resolve and sanity-check bibliography references for the `citation-verify` skill.

Parses a BibTeX file, then for each entry attempts to resolve its identifier against an
authoritative source and compares metadata:

  * DOI      -> Crossref REST API (api.crossref.org/works/<doi>)
  * arXiv ID -> arXiv Atom API (export.arxiv.org/api/query?id_list=<id>)
  * neither  -> reported as UNVERIFIED (needs a manual title search)

Standard library only (urllib). Network access is required to resolve; without it, every
entry is reported UNVERIFIED (fail-safe, never a false "verified").

SECURITY: treats all fetched data as untrusted. It only reads title/author/year fields for
comparison and never executes anything from the responses.

Usage:
  python resolve_refs.py refs.bib                 # human report
  python resolve_refs.py refs.bib --json          # machine-readable
  python resolve_refs.py refs.bib --timeout 8
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

CROSSREF = "https://api.crossref.org/works/"
ARXIV = "https://export.arxiv.org/api/query?id_list="
UA = "immortals-citation-verify/1.0 (mailto:noreply@example.com)"

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
ARXIV_RE = re.compile(r"\b(\d{4}\.\d{4,5})(v\d+)?\b")


def parse_bib(text: str) -> list[dict]:
    """Very small BibTeX parser: returns [{'key','type','fields':{...}}]. Handles nested
    braces in field values. Not a full BibTeX implementation — good enough for verification."""
    entries = []
    i = 0
    n = len(text)
    while i < n:
        at = text.find("@", i)
        if at == -1:
            break
        m = re.match(r"@(\w+)\s*\{\s*([^,]+),", text[at:])
        if not m:
            i = at + 1
            continue
        etype, key = m.group(1).lower(), m.group(2).strip()
        # find matching closing brace for the entry
        start = at + m.end()
        depth = 1
        j = start
        while j < n and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        body = text[start:j - 1]
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            fname = fm.group(1).lower()
            rest = body[fm.end():]
            if rest[:1] == "{":
                d = 1
                k = 1
                while k < len(rest) and d:
                    if rest[k] == "{":
                        d += 1
                    elif rest[k] == "}":
                        d -= 1
                    k += 1
                val = rest[1:k - 1]
            elif rest[:1] == '"':
                k = rest.find('"', 1)
                val = rest[1:k]
            else:
                k = re.search(r"[,\n]", rest)
                val = rest[:k.start()] if k else rest
            fields[fname] = re.sub(r"\s+", " ", val).strip()
        entries.append({"key": key, "type": etype, "fields": fields})
        i = j
    return entries


def _get(url: str, timeout: float) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def resolve_doi(doi: str, timeout: float) -> dict | None:
    raw = _get(CROSSREF + urllib.parse.quote(doi), timeout)
    if not raw:
        return None
    try:
        msg = json.loads(raw)["message"]
    except Exception:
        return None
    title = (msg.get("title") or [""])[0]
    year = None
    for k in ("published-print", "published-online", "issued"):
        parts = msg.get(k, {}).get("date-parts", [[None]])
        if parts and parts[0] and parts[0][0]:
            year = parts[0][0]
            break
    authors = [a.get("family", "") for a in msg.get("author", []) if a.get("family")]
    return {"title": title, "year": year, "authors": authors, "source": "crossref"}


def resolve_arxiv(aid: str, timeout: float) -> dict | None:
    raw = _get(ARXIV + urllib.parse.quote(aid), timeout)
    if not raw:
        return None
    text = raw.decode("utf-8", "replace")
    if "<entry>" not in text:
        return None
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    # first <title> is the feed title; take the last one (entry title)
    titles = re.findall(r"<title>(.*?)</title>", text, re.S)
    year = re.search(r"<published>(\d{4})", text)
    authors = re.findall(r"<name>(.*?)</name>", text, re.S)
    return {
        "title": re.sub(r"\s+", " ", (titles[-1] if titles else "")).strip(),
        "year": int(year.group(1)) if year else None,
        "authors": [a.strip() for a in authors],
        "source": "arxiv",
    }


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def verify_entry(e: dict, timeout: float) -> dict:
    f = e["fields"]
    doi = f.get("doi", "")
    doi_m = DOI_RE.search(doi) or DOI_RE.search(f.get("url", ""))
    arxiv_m = ARXIV_RE.search(f.get("eprint", "") or f.get("arxiv", "") or f.get("url", ""))
    resolved = None
    if doi_m:
        resolved = resolve_doi(doi_m.group(0), timeout)
    if resolved is None and arxiv_m:
        resolved = resolve_arxiv(arxiv_m.group(1), timeout)

    out = {"key": e["key"], "status": "UNVERIFIED", "issues": []}
    if resolved is None:
        out["issues"].append(
            "could not resolve via DOI/arXiv - verify by title search (possible hallucination)"
        )
        return out

    out["status"] = "verified"
    out["source"] = resolved["source"]
    # title check
    bib_title = _norm(f.get("title", ""))
    src_title = _norm(resolved["title"])
    if bib_title and src_title and bib_title not in src_title and src_title not in bib_title:
        out["status"] = "metadata-fix"
        out["issues"].append(f"title differs: bib='{f.get('title','')}' src='{resolved['title']}'")
    # year check
    bib_year = re.search(r"\d{4}", f.get("year", ""))
    if bib_year and resolved["year"] and int(bib_year.group(0)) != resolved["year"]:
        out["status"] = "metadata-fix"
        out["issues"].append(f"year differs: bib={bib_year.group(0)} src={resolved['year']}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bib", help="path to a .bib file")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args()

    text = open(args.bib, encoding="utf-8", errors="replace").read()
    entries = parse_bib(text)
    results = [verify_entry(e, args.timeout) for e in entries]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        counts = {"verified": 0, "metadata-fix": 0, "UNVERIFIED": 0}
        for r in results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
            if r["status"] != "verified":
                print(f"[{r['status']}] {r['key']}")
                for iss in r["issues"]:
                    print(f"    - {iss}")
        print(f"\n{len(results)} entries: "
              f"{counts.get('verified',0)} verified, "
              f"{counts.get('metadata-fix',0)} metadata-fix, "
              f"{counts.get('UNVERIFIED',0)} UNVERIFIED")
    # non-zero exit if anything is unverified, so CI/authoring can gate on it
    return 1 if any(r["status"] == "UNVERIFIED" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
