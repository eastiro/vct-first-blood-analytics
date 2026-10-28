"""Find and characterise the out-of-range coordinates."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\valorant-analytics")

rows = []
with (BASE / "data" / "rounds.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            rows.append(json.loads(line))

bad = []
for r in rows:
    if not r.get("geometry"):
        continue
    for k in r["kills"]:
        x, y = k.get("pos_x"), k.get("pos_y")
        if x is None or y is None:
            continue
        if not (0 <= x <= 1024 and 0 <= y <= 1024):
            bad.append((r, k))

print(f"out-of-range kill coords: {len(bad)}")
print("by map:", Counter(r["map"] for r, _ in bad))
print("by event:", Counter(r["event"] for r, _ in bad))
print("by key:", Counter(("pos" if not (0 <= k["pos_x"] <= 1024) else "") +
                         ("from" if k.get("from_x") is not None and
                          not (0 <= k["from_x"] <= 1024) else "")
                         for _, k in bad))

print("\nfirst 12:")
for r, k in bad[:12]:
    print(f"  {r['event'][:18]:<18} {r['map']:<9} r{r['round']:>2} "
          f"pos=({k['pos_x']:.1f},{k['pos_y']:.1f}) "
          f"from=({k.get('from_x')},{k.get('from_y')}) "
          f"killer={k['killer']} cause={k['cause']}")

# how far out?
ext = []
for r, k in bad:
    for x, y in ((k["pos_x"], k["pos_y"]), (k.get("from_x"), k.get("from_y"))):
        if x is None or y is None:
            continue
        if not (0 <= x <= 1024 and 0 <= y <= 1024):
            ext.append(max(abs(x), abs(y)))
print(f"\nworst absolute value: {max(ext):.1f}  (grid is 0..1024)")
print(f"count beyond by more than 50: {sum(1 for v in ext if v > 1074 or v < -50)}")
