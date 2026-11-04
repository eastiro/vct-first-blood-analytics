"""Inspect the crawl failures and retry them once."""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
from selectolax.lexbor import LexborHTMLParser  # noqa: E402

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
FAILS = BASE / "_cache" / "crawl_failures.jsonl"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def main() -> None:
    rows = [json.loads(l) for l in FAILS.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"failures: {len(rows)}")
    print("by event:", Counter(r["event"] for r in rows))
    print("by series:", len({r["series_id"] for r in rows}))

    with httpx.Client(trust_env=False, headers=HEADERS, timeout=45,
                      follow_redirects=True) as c:
        for r in rows[:8]:
            gid = r["game_id"]
            url = f"https://www.vlr.gg/{r['series_id']}?game={gid}&tab=logs"
            try:
                resp = c.get(url)
                html = resp.text
            except Exception as exc:
                print(f"  {r['series_id']}/{gid} ERR {type(exc).__name__}")
                time.sleep(1.2)
                continue
            dom = LexborHTMLParser(html)
            gids = [d.attributes.get("data-game-id") for d in dom.css("div.vm-stats-game")]
            rounds = dom.css("div.lg-round")
            empties = html.count("no data")
            print(f"  {r['series_id']}/{gid} {r['map']:<9} "
                  f"status={resp.status_code} bytes={len(html):>7} "
                  f"rounds={len(rounds):>2} page_gids={gids} 'no data'={empties}")
            time.sleep(1.2)


if __name__ == "__main__":
    main()
