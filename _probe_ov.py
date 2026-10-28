"""Check the overview tab, which DID render player stats in the browser.

If the stats exist server-side, they will be in this HTML.
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
URL = ("https://www.vlr.gg/777944/"
       "wolves-esports-vs-a-team-vct-china-2026-threshold-week-1-ro12/")
CACHE = Path(r"D:\好玩的项目\valorant-analytics\_cache\vlr_overview.html")


def get() -> str:
    if CACHE.exists():
        return CACHE.read_text(encoding="utf-8")
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        html = r.read().decode("utf-8", "replace")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(html, encoding="utf-8")
    return html


def text_of(f: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", f)).strip()


def main() -> None:
    html = get()
    print(f"bytes: {len(html)}")

    # player rows look like: <a href="/player/xxxx/name">Name</a>
    players = re.findall(r'href="/player/\d+/([a-z0-9\-_]+)"', html)
    print(f"\nplayer links: {len(set(players))}")
    print("  ", sorted(set(players))[:20])

    # agent icons
    agents = re.findall(r'/img/vlr/game/agents/([a-z0-9_]+)\.png', html)
    print(f"\nagent refs: {len(agents)}  distinct: {len(set(agents))}")
    print("  ", sorted(set(agents))[:25])

    # the stat cells: ACS etc appear as plain numbers in <td>
    tds = re.findall(r"<td[^>]*>(.*?)</td>", html, re.S)
    vals = [text_of(t) for t in tds]
    vals = [v for v in vals if v]
    print(f"\n<td> cells: {len(vals)}")
    print("  first 60:", vals[:60])

    # look for the ACS/K/D/A header row
    print("\nheader-ish strings:")
    for key in ("ACS", "K/D/A", "KAST", "ADR", "FK", "FD"):
        print(f"   {key}: {html.count(key)}")

    # round icons = end type per round
    rounds = re.findall(r"/game/round/([a-z]+)\.webp", html)
    print(f"\nround end-type icons: {len(rounds)}")
    from collections import Counter
    print("  ", Counter(rounds))


if __name__ == "__main__":
    main()
