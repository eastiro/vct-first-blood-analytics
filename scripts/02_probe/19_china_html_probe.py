"""What survives for China when data-map is absent?

If feed rows still carry killer/victim/cause/clock, then first-blood agent,
weapon, and timing analyses remain possible - only the spatial part dies.
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

URL = "https://www.vlr.gg/701025?game=273938&tab=logs"


def main() -> None:
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=40,
                      follow_redirects=True) as c:
        html = c.get(URL).text
    dom = LexborHTMLParser(html)
    game = dom.css_first('div.vm-stats-game[data-game-id="273938"]')
    print("game div:", game is not None)
    if game is None:
        return

    rounds = game.css("div.lg-round")
    print("round blocks:", len(rounds))
    r = rounds[0]
    print("round attrs:", dict(r.attributes))

    rows = r.css("div.lg-row")
    print(f"\nfeed rows in round 1: {len(rows)}")
    for row in rows[:6]:
        print("  --- row attrs:", dict(row.attributes))
        print("      text:", " | ".join(row.text(separator=" ").split())[:160])
        for sel in ("span.lg-source", "span.lg-site-text", "span.lg-kill",
                    "div.lg-kill", "span.lg-tag", "div.lg-row-inner"):
            el = row.css_first(sel)
            if el is not None:
                print(f"      {sel}: title={el.attributes.get('title')!r} "
                      f"text={el.text(strip=True)!r}")

    print("\n=== mirror/loadout block (buy phase) ===")
    for team_div in r.css(".lg-mir-team")[:2]:
        print(" team class:", team_div.attributes.get("class"))
        for lr in team_div.css(".lg-mir-row")[:3]:
            name = lr.css_first(".lg-mir-name")
            tag = lr.css_first(".lg-mir-tag")
            agent = lr.css_first(".lg-agent")
            gun = lr.css_first(".lg-kit-gun")
            shield = lr.css_first(".lg-kit-shield")
            spent = lr.css_first(".lg-kit-spent")
            left = lr.css_first(".lg-mir-left")
            print(f"   name={name.text(strip=True) if name else None!r} "
                  f"tag={tag.text(strip=True) if tag else None!r} "
                  f"agent={agent.attributes.get('title') if agent else None!r} "
                  f"gun={gun.attributes.get('title') if gun else None!r} "
                  f"shield={shield.attributes.get('title') if shield else None!r} "
                  f"spent={spent.text(strip=True) if spent else None!r} "
                  f"left={left.text(strip=True) if left else None!r}")

    print("\n=== band (team names) ===")
    for el in r.css("span.lg-band-team"):
        nm = el.css_first("span.lg-band-name")
        print("  class=", el.attributes.get("class"),
              "name=", (nm.attributes.get("title") or nm.text(strip=True)) if nm else None)


if __name__ == "__main__":
    main()
