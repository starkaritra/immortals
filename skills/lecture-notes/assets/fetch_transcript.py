#!/usr/bin/env python3
"""
lecture-notes :: transcript fetcher
Downloads and cleans captions from a lecture video or lists a playlist.

Usage:
  python fetch_transcript.py ensure                       # install yt-dlp if missing
  python fetch_transcript.py list  <playlist_or_video_url>  # -> "index|id|title" per line
  python fetch_transcript.py get   <video_url_or_id> [outdir]  # -> writes <id>.txt, prints path + word count

Notes:
  * Prefers manual/clean English captions (en-US / en), falls back to auto-generated.
  * VTT is de-duplicated and stripped of tags/timestamps into a single plain-text blob.
  * $0, deterministic, no API keys.
"""
import sys, os, re, subprocess, glob, json

YTDLP = [sys.executable, "-m", "yt_dlp"]

def ensure():
    try:
        subprocess.run(YTDLP + ["--version"], capture_output=True, check=True)
        return True
    except Exception:
        print("yt-dlp not found; installing ...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "yt-dlp"], check=True)
        return True

def norm_url(x):
    if re.fullmatch(r"[A-Za-z0-9_\-]{11}", x):
        return f"https://www.youtube.com/watch?v={x}"
    return x

def list_playlist(url):
    ensure()
    out = subprocess.run(
        YTDLP + ["--flat-playlist", "--print", "%(playlist_index)s|%(id)s|%(title)s", url],
        capture_output=True, text=True)
    sys.stdout.write(out.stdout)
    if out.returncode != 0:
        sys.stderr.write(out.stderr)
    return out.returncode

def clean_vtt(path):
    lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
    out = []
    for ln in lines:
        if "-->" in ln:                         continue
        if ln.strip() == "":                    continue
        if ln.startswith(("WEBVTT","Kind:","Language:","NOTE")): continue
        ln = re.sub(r"<[^>]+>", "", ln)         # inline timing tags
        ln = re.sub(r"\[.*?\]", "", ln)         # [Music] etc.
        ln = ln.strip()
        if not ln:                              continue
        if out and out[-1] == ln:               continue  # rolling-caption dupes
        out.append(ln)
    text = re.sub(r"\s+", " ", " ".join(out)).strip()
    return text

def get(url, outdir="."):
    ensure()
    url = norm_url(url)
    os.makedirs(outdir, exist_ok=True)
    # resolve the canonical video id first, so we only touch THIS video's files
    idr = subprocess.run(YTDLP + ["--no-warnings", "--skip-download", "--print", "%(id)s", url],
                         capture_output=True, text=True)
    vid = (idr.stdout.strip().splitlines() or [""])[0].strip()
    if not vid:
        print("ERROR: could not resolve video id", file=sys.stderr)
        return 2
    subprocess.run(
        YTDLP + ["--skip-download", "--write-auto-subs", "--write-subs",
                 "--sub-langs", "en.*", "--sub-format", "vtt",
                 "-o", os.path.join(outdir, "%(id)s.%(ext)s"), url],
        capture_output=True, text=True)
    # consider ONLY this video's caption files
    vtts = glob.glob(os.path.join(outdir, f"{vid}.*.vtt"))
    if not vtts:
        print("ERROR: no captions available for this video", file=sys.stderr)
        return 2
    def rank(p):
        b = os.path.basename(p)
        if ".en-US." in b: return (0, os.path.getsize(p))
        if b.endswith(".en.vtt"): return (1, os.path.getsize(p))
        return (2, os.path.getsize(p))
    best = sorted(vtts, key=rank)[0]
    text = clean_vtt(best)
    txt_path = os.path.join(outdir, f"{vid}.txt")
    open(txt_path, "w", encoding="utf-8").write(text)
    for p in vtts:                       # tidy up only this video's vtts
        try: os.remove(p)
        except OSError: pass
    print(json.dumps({"id": vid, "txt": txt_path, "words": len(text.split())}))
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "ensure":
        ensure(); print("yt-dlp ready")
    elif cmd == "list":
        sys.exit(list_playlist(sys.argv[2]))
    elif cmd == "get":
        outdir = sys.argv[3] if len(sys.argv) > 3 else "."
        sys.exit(get(sys.argv[2], outdir))
    else:
        print(__doc__); sys.exit(1)
