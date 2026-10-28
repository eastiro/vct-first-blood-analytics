"""Find the round-winner marker on both layouts."""
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

CASES = [
    ("geo", "https://www.vlr.gg/684613?game=270746&tab=logs"),
    ("feed", "https://www.vlr.gg/701025?game=273938&tab=logs"),
]


def main() -> None:
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=40,
                      follow_redirects=True) as c:
        for tag, url in CASES:
            html = c.get(url).text
            dom = LexborHTMLParser(html)
            game = dom.css_first("div.vm-stats-game.mod-active")
            print("=" * 70)
            print(tag, url)
            rounds = game.css("div.lg-round")
            print("rounds:", len(rounds))
            for rd in rounds[:8]:
                bands = [e.attributes.get("class") for e in rd.css("span.lg-band-team")]
                bis = rd.css_first("div.lg-band-mid")
                score = " ".join(bis.text(separator=" ").split()) if bis else ""
                print(f"  round={rd.attributes.get('data-round'):<3} "
                      f"bands={bands} mid={score!r}")

            # any element carrying mod-win?
            wins = game.css("[class*='mod-win']")
            print("  elements with mod-win:", len(wins))
            for w in wins[:5]:
                print("   ", w.attributes.get("class"), "| tag:", w.tag)


if __name__ == "__main__":
    main()
