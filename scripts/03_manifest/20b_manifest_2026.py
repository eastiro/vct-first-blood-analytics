"""Build the manifest for the 2026 events that are not crawled yet.

Missing from the current dataset
--------------------------------
- Valorant Masters Santiago 2026 (2760)      the FIRST Masters of 2026
- VCT 2026: {Americas,China,EMEA,Pacific} Kickoff  (2682/2685/2684/2683)
- VCT 2026: {Americas,China,EMEA,Pacific} Stage 1  (2860/2864/2863/2775)

Already crawled (not listed here): Masters London, Champions Shanghai,
and the four Stage 2 leagues.

Output: _cache/manifest_2026_add.json
The file is rewritten every 20 series so a crash does not lose everything.
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
OUT = BASE / "_cache" / "manifest_2026_add.json"

EVENTS: list[tuple[int, str, str]] = [
    (2760, "Masters Santiago 2026", "international"),
    (2682, "VCT Americas Kickoff 2026", "americas"),
    (2685, "VCT China Kickoff 2026", "china"),
    (2684, "VCT EMEA Kickoff 2026", "emea"),
    (2683, "VCT Pacific Kickoff 2026", "pacific"),
    (2860, "VCT Americas Stage 1 2026", "americas"),
    (2864, "VCT China Stage 1 2026", "china"),
    (2863, "VCT EMEA Stage 1 2026", "emea"),
    (2775, "VCT Pacific Stage 1 2026", "pacific"),
]

PAUSE = 0.7


def main() -> None:
    c = v.VLRClient(trust_env=False)
    entries: list[dict] = []

    for eid, ename, region in EVENTS:
        try:
            ms = c.event.matches(eid).matches
        except Exception as exc:  # noqa: BLE001
            print(f"=== {ename}: matches FAIL {type(exc).__name__}: {exc}", flush=True)
            continue
        done = [m for m in ms if m.status.value == "completed"]
        print(f"\n=== {ename} (event {eid}) : {len(done)}/{len(ms)} completed ===",
              flush=True)

        for i, m in enumerate(done, 1):
            teams = " vs ".join(t.name for t in m.teams)
            try:
                info = c.series.info(m.match_id)
            except Exception as exc:  # noqa: BLE001
                print(f"  [{i:>2}/{len(done)}] {m.match_id} info FAIL "
                      f"{type(exc).__name__}", flush=True)
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
            print(f"  [{i:>2}/{len(done)}] {m.match_id:<7} {str(m.stage)[:12]:<12} "
                  f"{teams[:40]:<40} maps={[g.map_name for g in played]}", flush=True)

            if i % 20 == 0:
                OUT.write_text(json.dumps(entries, ensure_ascii=False),
                               encoding="utf-8")
            time.sleep(PAUSE)

        OUT.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

    OUT.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(entries)} map entries -> {OUT}", flush=True)
    print("\n=== per event ===", flush=True)
    for eid, ename, _ in EVENTS:
        sub = [e for e in entries if e["event_id"] == eid]
        print(f"  {ename:<28} {len(sub):>3} maps", flush=True)


if __name__ == "__main__":
    main()
