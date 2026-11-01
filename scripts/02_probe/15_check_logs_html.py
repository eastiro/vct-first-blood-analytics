"""Check raw VLR logs HTML for a China Stage 2 series vs an EMEA one."""
from __future__ import annotations

import os
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
    ("china 701025 game273938", "https://www.vlr.gg/701025?game=273938&tab=logs"),
    ("china 701025 game1", "https://www.vlr.gg/701025?game=1&tab=logs"),
    ("emea 712803 game276498", "https://www.vlr.gg/712803?game=276498&tab=logs"),
]


def main() -> None:
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=30,
                      follow_redirects=True) as c:
        for label, url in CASES:
            print("=" * 70)
            print(label, url)
            try:
                r = c.get(url)
            except Exception as exc:
                print("  ERR", type(exc).__name__, exc)
                continue
            html = r.text
            print(f"  status={r.status_code} bytes={len(html)}")
            for probe in (
                "vm-stats-game-log",
                "wf-card mod-dark",
                "game-log",
                "vm-stats-game",
                "no data",
                "Round 1",
                "Buy",
                "vlr-rounds",
                "stats-game",
            ):
                print(f"   {probe!r:<22} count={html.count(probe)}")
            # show game ids present in the page
            import re
            ids = sorted(set(re.findall(r"[?&]game=(\d+)", html)))
            print("  game ids in page:", ids[:12])
            print()


if __name__ == "__main__":
    main()
