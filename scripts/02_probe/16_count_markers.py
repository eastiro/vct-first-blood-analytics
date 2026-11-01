"""Count replay structure markers on logs pages (China vs EMEA vs Champions)."""
from __future__ import annotations

import os
import re
import sys

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

CASES = [
    ("china s2 701025", "https://www.vlr.gg/701025?game=273938&tab=logs"),
    ("china s2 701030", "https://www.vlr.gg/701030?game=274000&tab=logs"),
    ("emea s2 712803", "https://www.vlr.gg/712803?game=276498&tab=logs"),
    ("masters london 684613", "https://www.vlr.gg/684613?game=270746&tab=logs"),
]

MARKERS = ['class="lg-round', "lg-map", "data-map", 'class="lg-row', "lg-band-team"]


def main() -> None:
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=30,
                      follow_redirects=True) as c:
        for label, url in CASES:
            r = c.get(url)
            html = r.text
            print("=" * 72)
            print(f"{label}  status={r.status_code} bytes={len(html)}")
            for m in MARKERS:
                print(f"   {m!r:<22} {html.count(m)}")
            # which game ids appear as vm-stats-game data-game-id
            gids = re.findall(r'vm-stats-game[^>]*data-game-id="(\d+)"', html)
            print("   vm-stats-game ids:", gids)
            print()


if __name__ == "__main__":
    main()
