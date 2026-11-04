"""Build the crawl manifest: every played map in the target events.

Targets
-------
- Valorant Masters London 2026   (event 2765) - the most recent Masters
- VCT 2026: EMEA Stage 2         (event 2976)
- VCT 2026: Americas Stage 2     (event 2977)
- VCT 2026: China Stage 2        (event 2978)
- VCT 2026: Pacific Stage 2      (event 2776)

Output: _cache/manifest.json  - one entry per played map game.
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
OUT = BASE / "_cache" / "manifest.json"

EVENTS: list[tuple[int, str, str]] = [
    (2765, "Masters London 2026", "international"),
    (2976, "VCT EMEA Stage 2", "emea"),
    (2977, "VCT Americas Stage 2", "americas"),
    (2978, "VCT China Stage 2", "china"),
    (2776, "VCT Pacific Stage 2", "pacific"),
]

PAUSE = 0.9


def main() -> None:
    c = v.VLRClient(trust_env=False)
    entries: list[dict] = []

    for eid, ename, region in EVENTS:
        ms = c.event.matches(eid).matches
        done = [m for m in ms if m.status.value == "completed"]
        print(f"\n=== {ename} (event {eid}) : {len(done)}/{len(ms)} completed series ===")

        for i, m in enumerate(done, 1):
            teams = " vs ".join(t.name for t in m.teams)
            try:
                info = c.series.info(m.match_id)
            except Exception as exc:
                print(f"  [{i:>2}/{len(done)}] {m.match_id} info FAIL {type(exc).__name__}")
                time.sleep(PAUSE)
                continue

            games = getattr(info, "games", []) or []
            played = [g for g in games if g.played]
            for gi, g in enumerate(games):
                if not g.played:
                    continue
                entries.append({
                    "event_id": eid,
                    "event": ename,
                    "region": region,
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
            print(f"  [{i:>2}/{len(done)}] {m.match_id:<7} {m.stage:<12} {teams:<40} "
                  f"maps={[g.map_name for g in played]}")
            time.sleep(PAUSE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"\nwrote {len(entries)} map entries -> {OUT}")
    print("\n=== per event ===")
    for eid, ename, _ in EVENTS:
        sub = [e for e in entries if e["event_id"] == eid]
        maps: dict[str, int] = {}
        for e in sub:
            maps[e["map"]] = maps.get(e["map"], 0) + 1
        print(f"  {ename:<24} {len(sub):>3} maps  {dict(sorted(maps.items(), key=lambda kv: -kv[1]))}")


if __name__ == "__main__":
    main()
