"""Verify the round-winner strip aligns with rounds and side swaps."""
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

URL = "https://www.vlr.gg/684613?game=270746&tab=logs"
FEED = "https://www.vlr.gg/701025?game=273938&tab=logs"


def inspect(url: str, tag: str) -> None:
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=40,
                      follow_redirects=True) as c:
        html = c.get(url).text
    dom = LexborHTMLParser(html)
    game = dom.css_first("div.vm-stats-game.mod-active")

    # all rnd-sq in document order
    squares = game.css("div.rnd-sq")
    print("=" * 70)
    print(tag, "rnd-sq count:", len(squares))
    print("  first 30 seq:", [s.attributes.get("class", "").replace("rnd-sq ", "")
                              for s in squares[:30]])

    # round blocks in document order with side mapping
    print("\n  per-round band sides:")
    for rd in game.css("div.lg-round"):
        rn = rd.attributes.get("data-round")
        sides = {}
        for el in rd.css("span.lg-band-team"):
            cls = el.attributes.get("class") or ""
            name_el = el.css_first("span.lg-band-name")
            nm = ""
            if name_el is not None:
                nm = name_el.attributes.get("title") or name_el.text(strip=True)
            side = "atk" if "mod-atk" in cls else "def" if "mod-def" in cls else "?"
            tno = "t1" if "mod-t1" in cls else "t2" if "mod-t2" in cls else "?"
            sides[tno] = (side, nm)
        print(f"    r{rn:<3} {sides}")

    # scoreboard in the header (round strip above the game) to cross-check
    print("\n  vlr-rounds strips:", len(dom.css("div.vlr-rounds-row-cons")))
    for strip in dom.css("div.vlr-rounds-row-cons")[:3]:
        sqs = strip.css("div.rnd-sq")
        print("    strip squares:", [s.attributes.get("class", "").replace("rnd-sq ", "")
                                     for s in sqs][:30])


if __name__ == "__main__":
    inspect(URL, "geo")
    inspect(FEED, "feed")
