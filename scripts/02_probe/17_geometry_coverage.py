"""Scan replay-geometry coverage across candidate events.

For each event, sample series and record whether the logs page carries the
`data-map` JSON blob (kill coordinates). Some events have kill feeds but no
geometry - we need to know how much before committing to a full crawl.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

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

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
OUT = BASE / "_cache" / "geometry_coverage.json"

EVENTS = {
    2765: "Masters London 2026",
    2976: "VCT 2026 EMEA S2",
    2977: "VCT 2026 Americas S2",
    2978: "VCT 2026 China S2",
    2776: "VCT 2026 Pacific S2",
}
# (event_id, match_id, game_id)
SAMPLES: list[tuple[int, int, int]] = []


def collect_samples() -> None:
    import vlrdevapi as v

    c = v.VLRClient(trust_env=False)
    for eid in EVENTS:
        ms = c.event.matches(eid).matches
        done = 0
        for m in ms:
            if m.status.value != "completed":
                continue
            try:
                info = c.series.info(m.match_id)
            except Exception as exc:
                print(f"  info FAIL {m.match_id}: {type(exc).__name__}")
                time.sleep(1.0)
                continue
            games = [g for g in (info.games or []) if g.played]
            if not games:
                time.sleep(1.0)
                continue
            # one map per series keeps the sample cheap but spread out
            g = games[len(games) // 2]
            SAMPLES.append((eid, m.match_id, g.game_id))
            done += 1
            time.sleep(0.8)
            if done >= 8:
                break
        print(f"event {eid} {EVENTS[eid]}: {done} samples")


def scan() -> None:
    rows = []
    with httpx.Client(trust_env=False, headers=HEADERS, timeout=40,
                      follow_redirects=True) as c:
        for i, (eid, mid, gid) in enumerate(SAMPLES, 1):
            url = f"https://www.vlr.gg/{mid}?game={gid}&tab=logs"
            try:
                r = c.get(url)
                html = r.text
            except Exception as exc:
                print(f"  [{i}/{len(SAMPLES)}] {mid} ERR {type(exc).__name__}")
                time.sleep(1.2)
                continue
            has_geo = "data-map" in html
            n_rounds = html.count('class="lg-round')
            n_rows = html.count('class="lg-row')
            matches = re.search(r'vm-stats-game[^>]*data-game-id="%d"' % gid, html)
            rows.append({
                "event_id": eid, "event": EVENTS[eid],
                "match_id": mid, "game_id": gid,
                "bytes": len(html), "has_geometry": has_geo,
                "round_blocks": n_rounds, "feed_rows": n_rows,
                "has_game_div": bool(matches),
            })
            print(f"  [{i}/{len(SAMPLES)}] {EVENTS[eid]:<22} {mid:<7} "
                  f"geo={'YES' if has_geo else 'no ':>3} "
                  f"rounds={n_rounds:>2} rows={n_rows:>3} bytes={len(html):>7}")
            time.sleep(1.2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== per-event coverage ===")
    for eid, name in EVENTS.items():
        sub = [r for r in rows if r["event_id"] == eid]
        if not sub:
            print(f"  {name:<24} no samples")
            continue
        ok = sum(1 for r in sub if r["has_geometry"])
        print(f"  {name:<24} {ok}/{len(sub)} with geometry")


if __name__ == "__main__":
    collect_samples()
    print(f"\nsamples: {len(SAMPLES)}")
    scan()
