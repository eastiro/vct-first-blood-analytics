"""Fetch VLR minimaps for every map seen in the manifest.

VLR's `/img/vlr/game/minimap/dark/{map}.png` (1024x1024) was verified to
align with the kill coordinates, unlike valorant-api's displayIcon.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\vct-first-blood-analytics")
MANIFEST = BASE / "_cache" / "manifest.json"
OUTDIR = BASE / "maps"
OUTDIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/png,image/*,*/*;q=0.8",
    "Referer": "https://www.vlr.gg/",
}


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    names = sorted({e["map"] for e in entries})
    print("maps in manifest:", names)

    ok, bad = [], []
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=40,
                      follow_redirects=True) as c:
        for m in names:
            slug = m.lower().replace(" ", "")
            url = f"https://www.vlr.gg/img/vlr/game/minimap/dark/{slug}.png"
            dest = OUTDIR / f"{slug}.png"
            if dest.exists() and dest.stat().st_size > 5000:
                print(f"  cached {m:<10} {dest.stat().st_size:>7} bytes")
                ok.append(m)
                continue
            try:
                r = c.get(url)
            except Exception as exc:
                print(f"  FAIL  {m:<10} {type(exc).__name__}")
                bad.append(m)
                time.sleep(1.0)
                continue
            if r.status_code == 200 and len(r.content) > 5000:
                dest.write_bytes(r.content)
                print(f"  ok    {m:<10} {len(r.content):>7} bytes -> {dest.name}")
                ok.append(m)
            else:
                print(f"  BAD   {m:<10} status={r.status_code} "
                      f"bytes={len(r.content)}")
                bad.append(m)
            time.sleep(0.9)

    print(f"\nfetched {len(ok)}/{len(names)}")
    if bad:
        print("missing:", bad)


if __name__ == "__main__":
    main()
