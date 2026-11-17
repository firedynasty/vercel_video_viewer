#!/usr/bin/env python3
"""Write ../videos.txt: one line per youtube/<ID>/ folder -> ID, title, link, and what's in it.

  python3 list_videos.py
Titles come from YouTube oEmbed (no key) and are reused from the previous videos.txt.
"""
import json, urllib.parse, urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SRC, OUT = BASE / "youtube", BASE / "videos.txt"

old = {}
if OUT.exists():
    for line in OUT.read_text(encoding="utf-8").splitlines():
        parts = line.split("  |  ")
        if len(parts) >= 2:
            old[parts[0]] = parts[1]


def title(vid):
    if vid in old:
        return old[vid]
    url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(
        f"https://www.youtube.com/watch?v={vid}", safe="")
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.load(r)["title"]
    except Exception:
        return "(no title found)"


lines = []
for d in sorted((p for p in SRC.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
    has = [k for k, pat in (("srt", "*.srt"), ("shifted", "*_shifted.srt"), ("gloss", "*.gloss.json"))
           if any(d.glob(pat))]
    lines.append(f"{d.name}  |  {title(d.name)}  |  https://youtu.be/{d.name}  |  {', '.join(has) or 'empty'}")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
print(f"\n{len(lines)} videos -> {OUT}")
