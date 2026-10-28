"""Where do lg-agent icons live in the China page, and can we get killer/victim agents?"""
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
    game = dom.css_first("div.vm-stats-game.mod-active")

    agents = game.css(".lg-agent")
    print("lg-agent icons:", len(agents))
    for a in agents[:6]:
        print("  title:", a.attributes.get("title"), "| src:", a.attributes.get("src"))

    print("\n=== first round rows, full inner HTML of row 0 ===")
    r0 = game.css_first("div.lg-round")
    row = r0.css_first("div.lg-row")
    print(row.html[:1200])

    print("\n=== per-row agent titles ===")
    for row in r0.css("div.lg-row")[:4]:
        titles = [a.attributes.get("title") for a in row.css(".lg-agent")]
        print(f"  ev={row.attributes.get('data-ev')} agents={titles}")

    print("\n=== lg-side / lg-feed structure ===")
    for side in r0.css("div.lg-side")[:2]:
        print("  side class:", side.attributes.get("class"))
        print("   ", side.text(separator="|", strip=True)[:200])


if __name__ == "__main__":
    main()
