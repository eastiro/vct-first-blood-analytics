"""Confirm winner_team is populated on a few maps (geo + feed)."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
from selectolax.lexbor import LexborHTMLParser  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import importlib  # noqa: E402

crawl = importlib.import_module("30_crawl")

MANIFEST = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics\_cache\manifest.json")


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    picks = [entries[0], entries[-1],
             next(e for e in entries if e["region"] == "china"),
             next(e for e in entries if e["region"] == "emea")]

    with httpx.Client(trust_env=False, headers=crawl.HEADERS,
                      timeout=crawl.TIMEOUT, follow_redirects=True) as c:
        for e in picks:
            url = f"https://www.vlr.gg/{e['series_id']}?game={e['game_id']}&tab=logs"
            html = crawl.fetch(c, url)
            dom = LexborHTMLParser(html)
            rounds = crawl._parse_geometry_rounds(dom, e["game_id"])
            layout = "geo"
            if rounds is None:
                rounds = crawl._parse_feedonly_rounds(dom, e["game_id"])
                layout = "feed"
            counts: dict[str, int] = {}
            for r in rounds:
                w = r.get("winner_team") or ""
                counts[w] = counts.get(w, 0) + 1
            print(f"{layout} {e['map']:<9} expect {e['score1']}-{e['score2']} "
                  f"| parsed {counts}")
            time.sleep(1.2)


if __name__ == "__main__":
    main()
