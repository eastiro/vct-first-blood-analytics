"""Inspect one round's player_stats in detail -- economy, loadout, ability casts."""
from __future__ import annotations

import json
from pathlib import Path

CACHE = Path(r"D:\好玩的项目\valorant-analytics\_sample_match.json")


def main() -> None:
    m = json.loads(CACHE.read_text(encoding="utf-8"))["data"][0]
    rounds = m["rounds"]

    print("=" * 72)
    print("PER-ROUND PER-PLAYER  (round 0)")
    print("=" * 72)
    r0 = rounds[0]
    print("round scalars:", {k: v for k, v in r0.items()
                            if not isinstance(v, (dict, list))})

    stats = r0["player_stats"]
    print(f"\nplayer_stats: {len(stats)} players")
    s0 = stats[0]
    print("\nkeys per player-round:")
    for k, v in s0.items():
        t = f"list[{len(v)}]" if isinstance(v, list) else (
            "dict" if isinstance(v, dict) else type(v).__name__)
        print(f"   {k:<28} {t}")

    print("\nfull economy block:")
    print(json.dumps(s0.get("economy", {}), ensure_ascii=False, indent=2))

    print("\nability block:")
    for key in ("ability", "ability_casts"):
        if key in s0:
            print(f"  {key}: {json.dumps(s0[key], ensure_ascii=False)}")

    print("\ndamage block:")
    for key in ("damage", "damage_events"):
        if key in s0:
            v = s0[key]
            if isinstance(v, list):
                print(f"  {key}: list[{len(v)}]")
                if v:
                    print("   ", json.dumps(v[0], ensure_ascii=False)[:300])
            else:
                print(f"  {key}: {v}")

    print("\n" + "=" * 72)
    print("ROUND-BY-ROUND ECONOMY ACROSS THE WHOLE MATCH")
    print("=" * 72)
    for i, r in enumerate(rounds):
        tot = {"Blue": 0, "Red": 0}
        for ps in r["player_stats"]:
            eco = ps.get("economy", {})
            v = eco.get("loadout_value") or 0
            tot[ps["player_team"]] = tot.get(ps["player_team"], 0) + v
        print(f"  R{i+1:>2}  {r['winning_team']:<5} {r['end_type']:<12} "
              f"plant={str(r['bomb_planted'])[0]} "
              f"Blue={tot['Blue']:>6,}  Red={tot['Red']:>6,}")


if __name__ == "__main__":
    main()
