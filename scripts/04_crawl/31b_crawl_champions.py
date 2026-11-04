"""Crawl the Champions 2026 manifest into a separate JSONL (resumable)."""
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

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
MANIFEST = BASE / "_cache" / "manifest_champions.json"
OUT = BASE / "data" / "rounds_champions.jsonl"
FAILS = BASE / "_cache" / "crawl_failures_champions.jsonl"
PAUSE = 1.1


def main() -> None:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    done = set()
    if OUT.exists():
        with OUT.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    done.add((r["series_id"], r["game_id"]))
    print(f"manifest {len(entries)} · already {len(done)}")

    todo = [e for e in entries if (e["series_id"], e["game_id"]) not in done]
    print(f"to crawl {len(todo)}")

    n_geo = n_feed = n_fail = 0
    n_rounds = n_kills = 0

    with httpx.Client(trust_env=False, headers=crawl.HEADERS,
                      timeout=crawl.TIMEOUT, follow_redirects=True) as client, \
         OUT.open("a", encoding="utf-8") as fh, \
         FAILS.open("a", encoding="utf-8") as fh_fail:

        for i, e in enumerate(todo, 1):
            sid, gid = e["series_id"], e["game_id"]
            url = f"https://www.vlr.gg/{sid}?game={gid}&tab=logs"
            html = crawl.fetch(client, url)
            if html is None:
                n_fail += 1
                fh_fail.write(json.dumps(e) + "\n"); fh_fail.flush()
                print(f"  [{i:>2}/{len(todo)}] FAIL {sid}/{gid} {e['map']}")
                time.sleep(PAUSE); continue

            dom = LexborHTMLParser(html)
            rounds = crawl._parse_geometry_rounds(dom, gid)
            layout = "geo"
            if rounds is None:
                rounds = crawl._parse_feedonly_rounds(dom, gid)
                layout = "feed"
            if rounds is None:
                n_fail += 1
                fh_fail.write(json.dumps(e) + "\n"); fh_fail.flush()
                print(f"  [{i:>2}/{len(todo)}] EMPTY {sid}/{gid} {e['map']}")
                time.sleep(PAUSE); continue

            for rec in rounds:
                fh.write(json.dumps({
                    "event_id": e["event_id"], "event": e["event"],
                    "region": e["region"], "stage": e["stage"],
                    "phase": e["phase"], "series_id": sid, "game_id": gid,
                    "game_no": e["game_no"], "map": e["map"],
                    "teams": e["teams"], "date": e["match_date"],
                    "score": f"{e['score1']}-{e['score2']}",
                    **rec,
                }, ensure_ascii=False) + "\n")
            fh.flush()

            k = sum(len(r["kills"]) for r in rounds)
            n_rounds += len(rounds); n_kills += k
            if layout == "geo": n_geo += 1
            else: n_feed += 1
            print(f"  [{i:>2}/{len(todo)}] {layout:<4} {e['stage']:<11} "
                  f"{e['map']:<9} r={len(rounds):>2} k={k:>3} {e['teams'][:34]}")
            time.sleep(PAUSE)

    print(f"\n=== done === geo {n_geo} · feed {n_feed} · fail {n_fail} · "
          f"rounds {n_rounds} · kills {n_kills}")
    print(f"{OUT} ({OUT.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
