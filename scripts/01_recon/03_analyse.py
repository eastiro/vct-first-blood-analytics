"""Analyse first bloods on Ascent from Champions 2026.

Questions:
  1. where on the map do first bloods happen
  2. which agents get them
  3. which weapons (and at what range)
  4. does the attacking or defending side get them more often
  5. how much does the opening duel predict the round
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(r"D:\好玩的项目\valorant-analytics\data\ascent_rounds.jsonl")


def load() -> list[dict]:
    return [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]


def is_pistol_round(round_no: int) -> bool:
    return round_no in (1, 13)


def main() -> None:
    rounds = load()
    print(f"rounds: {len(rounds)}   games: {len({r['game_id'] for r in rounds})}")

    total_kills = sum(len(r["kills"]) for r in rounds)
    print(f"kills:  {total_kills}")

    no_fb = 0
    fb_rows = []
    for r in rounds:
        ks = r["kills"]
        if not ks:
            no_fb += 1
            continue
        fb = min(ks, key=lambda k: (k["seconds"] if k["seconds"] is not None else 999))
        fb_rows.append({
            "round": r["round"],
            "game_id": r["game_id"],
            "attacking": r["attacking"],
            "pistol": is_pistol_round(r["round"]),
            "killer": fb["killer"],
            "killer_team": fb["killer_team"],
            "agent": fb["killer_agent"],
            "weapon": fb["cause"],
            "x": fb["pos_x"], "y": fb["pos_y"],
            "fx": fb["from_x"], "fy": fb["from_y"],
            "dist": fb["distance"],
            "seconds": fb["seconds"],
            "victim_agent": fb["victim_agent"],
        })

    print(f"rounds with a first blood: {len(fb_rows)}  (none: {no_fb})")

    print("\n" + "=" * 70)
    print("1. AGENT THAT GETS FIRST BLOOD")
    print("=" * 70)
    ag = Counter(r["agent"] for r in fb_rows)
    tot = sum(ag.values())
    for a, n in ag.most_common():
        print(f"   {str(a):<12} {n:>3}  {n/tot*100:>5.1f}%")

    print("\n" + "=" * 70)
    print("2. WEAPON USED FOR FIRST BLOOD")
    print("=" * 70)
    wp = Counter(r["weapon"] for r in fb_rows)
    for w, n in wp.most_common():
        print(f"   {str(w):<16} {n:>3}  {n/tot*100:>5.1f}%")

    print("\n" + "=" * 70)
    print("3. RANGE OF THE OPENING DUEL (minimap units)")
    print("=" * 70)
    ds = sorted(r["dist"] for r in fb_rows if r["dist"] is not None)
    if ds:
        n = len(ds)
        def pct(p): return ds[int(n * p)]
        print(f"   count {n}")
        print(f"   min {ds[0]:.0f}   p25 {pct(.25):.0f}   median {pct(.5):.0f}   "
              f"p75 {pct(.75):.0f}   max {ds[-1]:.0f}")
        buckets = [(0, 100), (100, 200), (200, 300), (300, 500), (500, 9999)]
        for lo, hi in buckets:
            c = sum(1 for d in ds if lo <= d < hi)
            print(f"   {lo:>3}-{hi if hi < 9999 else '+':<4} : {c:>3}  "
                  f"{'#' * int(c / max(1, n) * 60)}")

    print("\n" + "=" * 70)
    print("4. ATTACK vs DEFEND")
    print("=" * 70)
    side = Counter()
    for r in fb_rows:
        # killer_team is the side name as VLR uses it; attacking tells us which
        # team was attacking, so compare killer_team against that.
        if r["killer_team"] and r["attacking"]:
            side["attacker got FB" if r["killer_team"] == r["attacking"]
                 else "defender got FB"] += 1
    for k, v in side.most_common():
        print(f"   {k:<20} {v:>3}  {v/len(fb_rows)*100:>5.1f}%")

    print("\n" + "=" * 70)
    print("5. PISTOL ROUNDS vs GUN ROUNDS  (agents)")
    print("=" * 70)
    for flag, label in ((True, "pistol"), (False, "gun")):
        sub = [r for r in fb_rows if r["pistol"] is flag]
        c = Counter(r["agent"] for r in sub)
        print(f"\n   {label} rounds (n={len(sub)}):")
        for a, n in c.most_common(6):
            print(f"      {str(a):<12} {n:>3}")

    # save the first-blood table for plotting
    out = DATA.parent / "ascent_first_bloods.json"
    out.write_text(json.dumps(fb_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nfirst-blood table -> {out}")


if __name__ == "__main__":
    main()
