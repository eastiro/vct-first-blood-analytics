"""China logs pages: what EXACTLY can we extract?

No `data-map` blob -> no coordinates, no buy-phase loadouts, no alive
snapshots. Question: do the feed rows still give killer / victim / weapon /
clock reliably enough to compute first-blood agent + weapon + timing?
"""
from __future__ import annotations

import os
import sys

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
from selectolax.lexbor import LexborHTMLParser  # noqa: E402

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

URLS = [
    ("china", "https://www.vlr.gg/701025?game=273938&tab=logs"),
    ("emea", "https://www.vlr.gg/712803?game=276498&tab=logs"),
]


def main() -> None:
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=40,
                      follow_redirects=True) as c:
        for tag, url in URLS:
            html = c.get(url).text
            dom = LexborHTMLParser(html)
            print("=" * 74)
            print(tag, url)

            game = dom.css_first("div.vm-stats-game.mod-active")
            print("  active game div:", game is not None)
            if game is None:
                continue

            # classes present inside a round block
            r0 = game.css_first("div.lg-round")
            print("  round class:", r0.attributes.get("class"))
            print("  lg-round inner classes:",
                  sorted({n.attributes.get("class") for n in r0.css("div")})[:12])

            print("  lg-mir present:", len(game.css(".lg-mir")),
                  "| lg-mir-team:", len(game.css(".lg-mir-team")),
                  "| lg-kit-gun:", len(game.css(".lg-kit-gun")),
                  "| lg-agent:", len(game.css(".lg-agent")))

            # feed row detail
            rows = r0.css("div.lg-row")
            print(f"  rows in round 1: {len(rows)}")
            for row in rows:
                cls = row.attributes.get("class", "")
                ev = row.attributes.get("data-ev")
                src = row.css_first("span.lg-source")
                cells = [t.text(strip=True) for t in row.css("div.lg-cell, span")]
                print(f"    ev={ev:<3} class={cls:<18} "
                      f"src={src.attributes.get('title') if src else None!r:<10} "
                      f"cells={cells}")
            print()

    # do other maps carry the same structure? check a China Ascents map
    print("=" * 74)
    print("checking a China game where map == Ascent (event 2978)")


if __name__ == "__main__":
    main()
