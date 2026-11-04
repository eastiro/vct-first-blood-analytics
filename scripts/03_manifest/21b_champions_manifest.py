"""Add Valorant Champions 2026 (Shanghai) to the manifest and crawl it.

Event 2766, 2026-09-24..10-19, venue Shanghai. It was out of scope in the
first pass ("last Masters + four Stage 2 leagues"), but it is the season's
most important event, so it belongs in the dataset.
"""
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

import vlrdevapi as v  # noqa: E402

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
OUT = BASE / "_cache" / "manifest_champions.json"
EVENT_ID = 2766
PAUSE = 0.9


def main() -> None:
    c = v.VLRClient(trust_env=False)
    info = c.event.info(EVENT_ID)
    print(f"event: {info.name}")
    print(f"  dates : {info.start_date} .. {info.end_date}")
    print(f"  venue : {info.location}")
    print(f"  stages: {[s.name for s in (getattr(info, 'stage', None) or [])]}")

    ms = c.event.matches(EVENT_ID).matches
    done = [m for m in ms if m.status.value == "completed"]
    print(f"  series: {len(done)}/{len(ms)} completed\n")

    entries = []
    for i, m in enumerate(done, 1):
        teams = " vs ".join(t.name for t in m.teams)
        try:
            sinfo = c.series.info(m.match_id)
        except Exception as exc:
            print(f"  [{i:>2}/{len(done)}] {m.match_id} FAIL {type(exc).__name__}")
            time.sleep(PAUSE)
            continue
        games = getattr(sinfo, "games", []) or []
        played = [g for g in games if g.played]
        for gi, g in enumerate(games):
            if not g.played:
                continue
            entries.append({
                "event_id": EVENT_ID,
                "event": "Champions Shanghai 2026",
                "region": "international",
                "stage": m.stage,
                "phase": m.phase,
                "match_date": m.match_date.isoformat() if m.match_date else None,
                "series_id": m.match_id,
                "game_no": gi + 1,
                "game_id": g.game_id,
                "map": g.map_name,
                "score1": g.team1_score,
                "score2": g.team2_score,
                "teams": teams,
            })
        print(f"  [{i:>2}/{len(done)}] {m.match_id:<7} {m.stage:<12} "
              f"{teams:<42} maps={[g.map_name for g in played]}")
        time.sleep(PAUSE)

    OUT.write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(entries)} map entries -> {OUT}")

    from collections import Counter
    print("maps:", dict(Counter(e["map"] for e in entries).most_common()))


if __name__ == "__main__":
    main()
