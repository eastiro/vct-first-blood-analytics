"""Scrape the VLR match page 'economy' tab and report what is actually available.

Single request, cached to disk. No bulk crawling: one page, once.
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
URL = ("https://www.vlr.gg/777944/"
       "wolves-esports-vs-a-team-vct-china-2026-threshold-week-1-ro12/?tab=economy")
CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache\vlr_economy.html")


def get() -> str:
    if CACHE.exists():
        return CACHE.read_text(encoding="utf-8")
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        html = r.read().decode("utf-8", "replace")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(html, encoding="utf-8")
    return html


def text_of(fragment: str) -> str:
    s = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    html = get()
    print(f"html bytes: {len(html)}")

    # VLR marks the tab body with these
    for marker in ("vm-stats-game", "wf-table", "vm-stats-game-header",
                   "economy", "vm-stats"):
        print(f"  contains {marker!r}: {html.count(marker)}")

    print("\n" + "=" * 72)
    print("HEADINGS / TABLE HEADERS FOUND")
    print("=" * 72)
    heads = re.findall(r"<th[^>]*>(.*?)</th>", html, re.S)
    for h in heads[:40]:
        t = text_of(h)
        if t:
            print("  TH:", t[:60])

    print("\n" + "=" * 72)
    print("PLACEHOLDER / EMPTY-STATE MESSAGES")
    print("=" * 72)
    for pat in (r'class="[^"]*wf-card-mod[^"]*"', r"No data", r"not available",
                r"vm-stats-game-none", r"Empty"):
        for m in re.finditer(pat, html):
            frag = html[max(0, m.start() - 100): m.start() + 200]
            t = text_of(frag)
            if t:
                print(f"  [{pat}] {t[:140]}")
                break

    print("\n" + "=" * 72)
    print("ROUND-BY-ROUND ECONOMY CELLS (looking for credit numbers)")
    print("=" * 72)
    # credit values typically appear as comma groups like 3,900 or 3900
    nums = re.findall(r">\s*([0-9]{1,2},[0-9]{3})\s*<", html)
    print(f"  comma-formatted credit values: {len(nums)}")
    if nums:
        print("  first 30:", nums[:30])


if __name__ == "__main__":
    main()
