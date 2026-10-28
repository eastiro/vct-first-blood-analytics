"""Pull the replay for the Champions 2026 Grand Final and print real first-blood data.

This is the decisive test: if pos_x/pos_y/agent/cause come back, the analysis the
user wants (first-blood locations on Ascent by agent and weapon) is feasible.
"""
from __future__ import annotations

import os
from collections import Counter

for _k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

import vlrdevapi as v  # noqa: E402
from vlrdevapi._series.replay.models import ReplayEventType  # noqa: E402

SERIES_ID = 754737
GAME_ID = 283286      # map 1: Summit


def main() -> None:
    c = v.VLRClient(trust_env=False)
    rep = c.series.replay(SERIES_ID, GAME_ID)

    print(f"{rep.team1} vs {rep.team2}")
    print(f"rounds returned: {rep.num_rounds}")

    if not rep.rounds:
        print("\nNO REPLAY DATA for this game.")
        return

    r1 = rep.rounds[0]
    print(f"\n--- round 1 ---  attacking={r1.attacking}  "
          f"events={len(r1.events)}  loadouts={len(r1.loadouts)}")

    print("\nloadouts (buy phase):")
    for ld in r1.loadouts[:10]:
        print(f"   {ld.name:<12} {ld.team:<14} {str(ld.agent):<10} "
              f"{str(ld.weapon):<12} armor={ld.armor} spent={ld.spent} left={ld.credits_left}")

    print("\nround-1 timeline:")
    for ev in r1.events:
        act = ev.actor.name if ev.actor else "-"
        vict = ev.victim.name if ev.victim else "-"
        print(f"   {ev.seq:>2}. {ev.clock or '?':<7} {str(ev.type.value):<9} "
              f"{act:<12} -> {vict:<12} cause={ev.cause} "
              f"pos=({ev.pos_x},{ev.pos_y}) from=({ev.from_x},{ev.from_y}) "
              f"dist={ev.distance_units}")

    # ---- aggregate every first blood in the match ----
    print("\n" + "=" * 70)
    print("FIRST BLOODS ACROSS ALL ROUNDS")
    print("=" * 70)
    agents, causes, count = Counter(), Counter(), 0
    rows = []
    for rd in rep.rounds:
        kills = [e for e in rd.events if e.type is ReplayEventType.KILL]
        if not kills:
            continue
        fb = kills[0]
        count += 1
        a = fb.actor.agent if fb.actor else "?"
        agents[a] += 1
        causes[fb.cause] += 1
        rows.append((rd.round_number, rd.attacking, a, fb.cause,
                     fb.pos_x, fb.pos_y, fb.distance_units))

    for r in rows:
        print(f"   R{r[0]:>2} ({r[1]:<7}) agent={str(r[2]):<10} weapon={str(r[3]):<14} "
              f"pos=({r[4]},{r[5]}) dist={r[6]}")

    print(f"\nfirst bloods found: {count}")
    print("by agent :", agents.most_common())
    print("by weapon:", causes.most_common())


if __name__ == "__main__":
    main()
