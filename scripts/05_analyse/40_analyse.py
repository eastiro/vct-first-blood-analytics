"""Analyse first-blood data across the 2026 target events.

Produces the tables the site and the CV need:

1. per-map first-blood counts and attacker/defender split
2. first-blood -> round-win conversion, overall and per map
3. conversion by opening-duel weapon class (pistol / rifle / sniper / SMG / ability)
4. conversion by first-blood timing bucket
5. agent and weapon leaderboards (Chinese + English names)
6. spatial statistics where geometry exists (distance, site)

All outputs are plain JSON so a static front-end can consume them directly.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(r"D:\好玩的项目\vct-first-blood-analytics")
SRC = BASE / "data" / "rounds.jsonl"
OUT = BASE / "data" / "analysis.json"

# weapon -> class. Anything not listed is treated as an ability/ult.
WEAPON_CLASS = {
    # sidearms
    "Classic": "pistol", "Shorty": "pistol", "Frenzy": "pistol",
    "Ghost": "pistol", "Sheriff": "pistol",
    # SMG
    "Stinger": "smg", "Spectre": "smg",
    # shotguns
    "Bucky": "shotgun", "Judge": "shotgun",
    # rifles
    "Bulldog": "rifle", "Guardian": "rifle", "Phantom": "rifle",
    "Vandal": "rifle",
    # snipers
    "Marshal": "sniper", "Outlaw": "sniper", "Operator": "sniper",
    # LMG
    "Ares": "lmg", "Odin": "lmg",
    # melee
    "Melee": "melee",
    # new sidearms seen in 2026 data
    "Bandit": "pistol",
}


def weapon_class(cause: str) -> str:
    if not cause:
        return "unknown"
    return WEAPON_CLASS.get(cause.strip(), "ability")


def pct(n: int, d: int) -> float | None:
    return round(100.0 * n / d, 1) if d else None


def load() -> list[dict]:
    rows = []
    with SRC.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def first_kill(round_rec: dict) -> dict | None:
    kills = [k for k in (round_rec.get("kills") or []) if k.get("killer")]
    if not kills:
        return None
    return min(kills, key=lambda k: (k.get("seconds") if k.get("seconds") is not None else 9999))


def bucket_time(sec: int | None) -> str:
    if sec is None:
        return "unknown"
    if sec <= 10:
        return "0-10s"
    if sec <= 20:
        return "11-20s"
    if sec <= 30:
        return "21-30s"
    if sec <= 45:
        return "31-45s"
    return "46s+"


def main() -> None:
    rows = load()
    print(f"round rows: {len(rows)}")

    games = {(r["series_id"], r["game_id"]) for r in rows}
    print(f"distinct maps: {len(games)}")

    # ---- global tallies -------------------------------------------------
    fb_agents: Counter = Counter()
    fb_weapons: Counter = Counter()
    fb_classes: Counter = Counter()
    fb_by_map: dict[str, dict] = defaultdict(
        lambda: {"rounds": 0, "fb": 0, "atk_fb": 0, "def_fb": 0,
                 "fb_won": 0, "no_fb_rounds": 0}
    )
    conv_by_class: dict[str, dict] = defaultdict(lambda: {"n": 0, "won": 0})
    conv_by_bucket: dict[str, dict] = defaultdict(lambda: {"n": 0, "won": 0})
    conv_by_side: dict[str, dict] = defaultdict(lambda: {"n": 0, "won": 0})
    conv_by_event: dict[str, dict] = defaultdict(lambda: {"n": 0, "won": 0})
    distances: list[float] = []
    per_event_maps: dict[str, set] = defaultdict(set)
    fb_missing_winner = 0

    for r in rows:
        mp = r["map"]
        b = fb_by_map[mp]
        b["rounds"] += 1
        per_event_maps[r["event"]].add((r["series_id"], r["game_id"]))

        fk = first_kill(r)
        if fk is None:
            b["no_fb_rounds"] += 1
            continue

        b["fb"] += 1
        killer_team = fk.get("killer_team") or ""
        attacking = r.get("attacking") or ""
        is_atk = killer_team and attacking and killer_team == attacking
        b["atk_fb" if is_atk else "def_fb"] += 1

        fb_agents[fk.get("killer_agent") or "?"] += 1
        cause = (fk.get("cause") or "").strip()
        fb_weapons[cause or "?"] += 1
        wclass = weapon_class(cause)
        fb_classes[wclass] += 1

        win_team = r.get("winner_team") or ""
        if not win_team:
            fb_missing_winner += 1
            continue
        won = (killer_team == win_team)
        if won:
            b["fb_won"] += 1

        conv_by_class[wclass]["n"] += 1
        conv_by_class[wclass]["won"] += int(won)
        conv_by_bucket[bucket_time(fk.get("seconds"))]["n"] += 1
        conv_by_bucket[bucket_time(fk.get("seconds"))]["won"] += int(won)
        side_key = "attack" if is_atk else "defense"
        conv_by_side[side_key]["n"] += 1
        conv_by_side[side_key]["won"] += int(won)
        conv_by_event[r["event"]]["n"] += 1
        conv_by_event[r["event"]]["won"] += int(won)

        if fk.get("distance"):
            distances.append(float(fk["distance"]))

    # ---- assemble ------------------------------------------------------
    per_map = {}
    for mp, b in sorted(fb_by_map.items()):
        per_map[mp] = {
            "rounds": b["rounds"],
            "first_bloods": b["fb"],
            "no_first_blood_rounds": b["no_fb_rounds"],
            "fb_rate_pct": pct(b["fb"], b["rounds"]),
            "attacker_fb": b["atk_fb"],
            "defender_fb": b["def_fb"],
            "attacker_fb_pct": pct(b["atk_fb"], b["fb"]),
            "fb_to_win_pct": pct(b["fb_won"], b["fb"]),
            "events": sorted({r["event"] for r in rows if r["map"] == mp}),
        }

    def conv_block(d: dict, denom_name: str) -> dict:
        return {
            k: {"n": v["n"], "won": v["won"], "rate_pct": pct(v["won"], v["n"])}
            for k, v in sorted(d.items(), key=lambda kv: -kv[1]["n"])
        }

    total_fb = sum(fb_by_map[m]["fb"] for m in fb_by_map)
    total_fb_won = sum(fb_by_map[m]["fb_won"] for m in fb_by_map)

    result = {
        "meta": {
            "round_rows": len(rows),
            "maps": len(games),
            "events": sorted(per_event_maps),
            "maps_per_event": {k: len(v) for k, v in sorted(per_event_maps.items())},
            "total_first_bloods": total_fb,
            "overall_fb_to_win_pct": pct(total_fb_won, total_fb),
            "rounds_missing_winner_field": fb_missing_winner,
        },
        "per_map": per_map,
        "agents": [
            {"agent": a, "first_bloods": n, "share_pct": pct(n, total_fb)}
            for a, n in fb_agents.most_common()
        ],
        "weapons": [
            {"weapon": w, "class": weapon_class(w) if w != "?" else "unknown",
             "first_bloods": n, "share_pct": pct(n, total_fb)}
            for w, n in fb_weapons.most_common()
        ],
        "weapon_classes": [
            {"class": c, "first_bloods": n, "share_pct": pct(n, total_fb)}
            for c, n in fb_classes.most_common()
        ],
        "conversion_by_weapon_class": conv_block(conv_by_class, "class"),
        "conversion_by_time_bucket": conv_block(conv_by_bucket, "bucket"),
        "conversion_by_side": conv_block(conv_by_side, "side"),
        "conversion_by_event": conv_block(conv_by_event, "event"),
        "distance": {
            "n": len(distances),
            "median_units": round(statistics.median(distances), 1) if distances else None,
            "p10": round(statistics.quantiles(distances, n=10)[0], 1) if len(distances) > 10 else None,
            "p90": round(statistics.quantiles(distances, n=10)[-1], 1) if len(distances) > 10 else None,
            "max": round(max(distances), 1) if distances else None,
        } if distances else {},
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- console summary ----------------------------------------------
    print("\n=== maps / rounds / first bloods ===")
    print(f"  {'map':<10} {'rounds':>7} {'FB':>6} {'FB%':>6} {'atk%':>6} {'FB->win%':>9}")
    for mp, v in sorted(per_map.items(), key=lambda kv: -kv[1]["first_bloods"]):
        print(f"  {mp:<10} {v['rounds']:>7} {v['first_bloods']:>6} "
              f"{v['fb_rate_pct']:>6} {v['attacker_fb_pct']:>6} {v['fb_to_win_pct']:>9}")

    print(f"\n  overall FB->win: {result['meta']['overall_fb_to_win_pct']}%")

    print("\n=== conversion by weapon class ===")
    for k, v in result["conversion_by_weapon_class"].items():
        print(f"  {k:<10} n={v['n']:>6} won={v['won']:>6} {v['rate_pct']}%")

    print("\n=== conversion by time bucket ===")
    for k, v in result["conversion_by_time_bucket"].items():
        print(f"  {k:<10} n={v['n']:>6} {v['rate_pct']}%")

    print("\n=== conversion by side ===")
    for k, v in result["conversion_by_side"].items():
        print(f"  {k:<10} n={v['n']:>6} {v['rate_pct']}%")

    print("\n=== top agents ===")
    for a in result["agents"][:12]:
        print(f"  {a['agent']:<14} {a['first_bloods']:>5}  {a['share_pct']}%")

    print("\n=== top weapons ===")
    for w in result["weapons"][:12]:
        print(f"  {w['weapon']:<14} {w['class']:<8} {w['first_bloods']:>5}  {w['share_pct']}%")

    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
