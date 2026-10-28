"""Fetch a failing China game WITH tab=logs and dump what the page contains."""
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
    ("FAIL", "https://www.vlr.gg/701043?game=273983&tab=logs"),
    ("FAIL2", "https://www.vlr.gg/701045?game=273989&tab=logs"),
    ("OK", "https://www.vlr.gg/701025?game=273938&tab=logs"),
]


def main() -> None:
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=45,
                      follow_redirects=True) as c:
        for tag, url in CASES:
            print("=" * 74)
            r = c.get(url)
            html = r.text
            dom = LexborHTMLParser(html)
            print(f"{tag} {url}")
            print(f"  status={r.status_code} bytes={len(html)}")
            print(f"  lg-round total in doc : {html.count('class=\"lg-round')}")
            print(f"  lg-map total in doc   : {html.count('lg-map')}")
            print(f"  data-map total        : {html.count('data-map')}")

            for gd in dom.css("div.vm-stats-game"):
                print(f"   game={gd.attributes.get('data-game-id'):<8} "
                      f"rounds={len(gd.css('div.lg-round')):<3} "
                      f"rows={len(gd.css('div.lg-row')):<4} "
                      f"class={gd.attributes.get('class')}")

            # what tabs exist?
            tabs = [a.attributes.get("href") for a in dom.css("a.vm-stats-game-tab, .wf-tab a")]
            if tabs:
                print("  tabs:", tabs[:8])

            body = dom.css_first("div.vm-stats")
            if body is not None:
                txt = " ".join(body.text(separator=" ").split())
                print("  stats text head:", txt[:180])
            print()


if __name__ == "__main__":
    main()
