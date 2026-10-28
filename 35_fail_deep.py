"""Do the failing China games genuinely lack logs, or use another markup?

Compares a failing series against a working China series, dumping per-game-div
round counts.
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

CASES = [
    ("FAIL 701043", "https://www.vlr.gg/701043"),
    ("OK   701025", "https://www.vlr.gg/701025"),
]


def main() -> None:
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=45,
                      follow_redirects=True) as c:
        for tag, base in CASES:
            print("=" * 74)
            print(tag, base)
            html = c.get(base).text
            dom = LexborHTMLParser(html)

            for gd in dom.css("div.vm-stats-game"):
                gid = gd.attributes.get("data-game-id")
                n_rounds = len(gd.css("div.lg-round"))
                n_rows = len(gd.css("div.lg-row"))
                print(f"  game={gid:<8} lg-round={n_rounds:<3} lg-row={n_rows:<4}")

            # is the match even complete?
            hdr = dom.css_first("div.match-header")
            if hdr:
                txt = " ".join(hdr.text(separator=" ").split())
                print("  header:", txt[:160])

            # any explicit "no data" / TBD marker
            for probe in ("match-header-note", "wf-label mod-large",
                          "vm-stats-game-log", "No data"):
                if probe in html:
                    print(f"   marker present: {probe!r}")
            print()


if __name__ == "__main__":
    main()
