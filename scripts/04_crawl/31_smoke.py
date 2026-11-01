"""Smoke-test 30_crawl on a mix of geometry and feed-only pages."""
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

BASE = Path(r"D:\好玩的项目\vct-first-blood-analytics")
MANIFEST = BASE / "_cache" / "manifest.json"


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # 2 from each event
    picks = []
    seen: dict[int, int] = {}
    for e in entries:
        if seen.get(e["event_id"], 0) < 2:
            picks.append(e)
            seen[e["event_id"]] = seen.get(e["event_id"], 0) + 1
    print(f"testing {len(picks)} maps\n")

    with httpx.Client(trust_env=False, headers=crawl.HEADERS,
                      timeout=crawl.TIMEOUT, follow_redirects=True) as client:
        for e in picks:
            url = f"https://www.vlr.gg/{e['series_id']}?game={e['game_id']}&tab=logs"
            html = crawl.fetch(client, url)
            if html is None:
                print(f"  FETCH FAIL {e['event']} {e['map']}")
                time.sleep(1.2)
                continue
            dom = LexborHTMLParser(html)
            rounds = crawl._parse_geometry_rounds(dom, e["game_id"])
            layout = "geo"
            if rounds is None:
                rounds = crawl._parse_feedonly_rounds(dom, e["game_id"])
                layout = "feed"

            if rounds is None:
                print(f"  EMPTY {e['event']} {e['map']}")
                time.sleep(1.2)
                continue

            kills = sum(len(r["kills"]) for r in rounds)
            fb = rounds[0]["kills"][0] if rounds[0]["kills"] else None
            print(f"  {layout:<4} {e['event'][:20]:<20} {e['map']:<9} "
                  f"rounds={len(rounds):>2} kills={kills:>3} "
                  f"attacking={rounds[0]['attacking'][:16]!r}")
            if fb:
                print(f"        first blood: {fb['killer']}({fb['killer_agent']}) "
                      f"-> {fb['victim']}({fb['victim_agent']}) "
                      f"@ {fb['clock']} with {fb['cause']!r} "
                      f"dist={fb['distance']}")
            else:
                print("        !! round 1 has no kills")
            time.sleep(1.2)


if __name__ == "__main__":
    main()
