"""Probe: does a Stage 2 (regular season) series expose replay data?

Checks one series per event so we know whether the crawl is viable before
committing to ~270 series.
"""
from __future__ import annotations

import os
import sys

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vlrdevapi as v  # noqa: E402
from vlrdevapi._series.replay.models import ReplayEventType  # noqa: E402

SAMPLES = [
    (2765, 684613, "Masters London 2026 / Swiss R1"),
    (2976, 712803, "EMEA Stage 2 / Group Week 1"),
    (2977, 706349, "Americas Stage 2 / Group Week 1"),
    (2978, 701025, "China Stage 2 / Group Week 1"),
    (2776, 698884, "Pacific Stage 2 / Group Week 1"),
]


def main() -> None:
    c = v.VLRClient(trust_env=False)
    for eid, mid, label in SAMPLES:
        print("=" * 72)
        print(f"{label}   event={eid} series={mid}")
        try:
            info = c.series.info(mid)
        except Exception as exc:
            print("  info ERR", type(exc).__name__, exc)
            continue

        games = getattr(info, "games", []) or []
        print(f"  games: {len(games)}")
        for g in games:
            print(f"    game_id={g.game_id} map={g.map_name!r} played={g.played} "
                  f"score={g.team1_score}-{g.team2_score} dur={g.duration_seconds}")

        played = [g for g in games if g.played]
        if not played:
            print("  no played games")
            continue
        g0 = played[0]
        try:
            rep = c.series.replay(mid, g0.game_id)
        except Exception as exc:
            print("  replay ERR", type(exc).__name__, exc)
            continue
        print(f"  replay: rounds={rep.num_rounds} team1={rep.team1!r} team2={rep.team2!r}")
        if rep.rounds:
            r0 = rep.rounds[0]
            kills = [e for e in r0.events if e.type is ReplayEventType.KILL]
            print(f"  round1: attacking={r0.attacking!r} loadouts={len(r0.loadouts)} "
                  f"events={len(r0.events)} kills={len(kills)}")
            if kills:
                k = kills[0]
                print(f"    first kill: {k.actor.name if k.actor else '?'}"
                      f"({k.actor.agent if k.actor else '?'}) -> "
                      f"{k.victim.name if k.victim else '?'}"
                      f"({k.victim.agent if k.victim else '?'}) "
                      f"with {k.cause!r} at {k.clock} dist={k.distance_units}")
                print(f"    pos=({k.pos_x:.1f},{k.pos_y:.1f}) from=({k.from_x:.1f},{k.from_y:.1f})")
        print()


if __name__ == "__main__":
    main()
