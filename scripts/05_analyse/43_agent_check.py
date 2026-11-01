"""Is the agent distribution plausible? Check per-event and per-round agent sets."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\valorant-analytics")
SRC = BASE / "data" / "rounds.jsonl"

rows = []
with SRC.open(encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            rows.append(json.loads(line))


def first_kill(r):
    ks = [k for k in (r.get("kills") or []) if k.get("killer")]
    return min(ks, key=lambda k: (k.get("seconds") if k.get("seconds") is not None else 9999)) if ks else None


print("=== first-blood agent share by event ===")
for ev in sorted({r["event"] for r in rows}):
    c = Counter()
    for r in rows:
        if r["event"] != ev:
            continue
        fk = first_kill(r)
        if fk:
            c[(fk.get("killer_agent") or "?").lower()] += 1
    tot = sum(c.values())
    print(f"\n  {ev}  (n={tot})")
    for a, n in c.most_common(8):
        print(f"    {a:<12} {n:>5} {100*n/tot:>5.1f}%")

print("\n=== sanity: how many distinct agents appear per map ===")
by_map = defaultdict(set)
for r in rows:
    for k in (r.get("kills") or []):
        if k.get("killer_agent"):
            by_map[r["map"]].add(k["killer_agent"].lower())
for m, s in sorted(by_map.items()):
    print(f"  {m:<9} distinct killer agents = {len(s)}")

print("\n=== sample: one map's rounds, killer agents ===")
sample = [r for r in rows if r["event"] == "Masters London 2026" and r["map"] == "Ascent"][:6]
for r in sample:
    fk = first_kill(r)
    agents = [ (k.get("killer_agent") or '?') for k in r["kills"][:5] ]
    print(f"  r{r['round']:>2} fb={fk.get('killer_agent') if fk else None:<12} "
          f"first5={agents}")
