"""Sanity-check the data: rounds without kills, loadout coverage, winner coverage."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\vct-first-blood-analytics")
SRC = BASE / "data" / "rounds.jsonl"

rows = []
with SRC.open(encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            rows.append(json.loads(line))

print(f"round rows: {len(rows)}")

no_kills = [r for r in rows if not r.get("kills")]
print(f"rounds with zero kills: {len(no_kills)}")
for r in no_kills[:5]:
    print("   ", r["event"], r["map"], "round", r["round"], "winner", r.get("winner_team"))

no_winner = [r for r in rows if not r.get("winner_team")]
print(f"rounds with no winner_team: {len(no_winner)}")
for r in no_winner[:5]:
    print("   ", r["event"], r["map"], "round", r["round"], "geo", r.get("geometry"))

no_killer = [r for r in rows if r.get("kills") and not any(k.get("killer") for k in r["kills"])]
print(f"rounds whose kills all lack a killer name: {len(no_killer)}")

# loadout coverage by layout
geo = [r for r in rows if r.get("geometry")]
feed = [r for r in rows if not r.get("geometry")]
print(f"\ngeometry rows: {len(geo)}  with loadouts: {sum(1 for r in geo if r.get('loadouts'))}")
print(f"feed rows    : {len(feed)}  with loadouts: {sum(1 for r in feed if r.get('loadouts'))}")

# rounds per map distribution
print("\nrounds by map:")
for m, n in Counter(r["map"] for r in rows).most_common():
    print(f"  {m:<9} {n:>5}")

# geo share by event
print("\ngeometry share by event:")
for ev in sorted({r["event"] for r in rows}):
    sub = [r for r in rows if r["event"] == ev]
    g = sum(1 for r in sub if r.get("geometry"))
    print(f"  {ev:<22} {len(sub):>5} rounds, {g:>5} geo ({100*g/len(sub):.0f}%)")
