"""Pull the headline numbers for the write-up."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
A = json.loads((BASE / "data" / "analysis.json").read_text(encoding="utf-8"))

m = A["meta"]
print("=== meta ===")
for k, v in m.items():
    if k != "maps_per_event":
        print(f"  {k}: {v}")
print("  maps_per_event:", m["maps_per_event"])

print("\n=== per map ===")
for mp, v in sorted(A["per_map"].items(), key=lambda kv: -kv[1]["rounds"]):
    print(f"  {mp:<9} rounds={v['rounds']:>5} fb={v['first_bloods']:>5} "
          f"atk%={v['attacker_fb_pct']:>5} conv={v['fb_to_win_pct']:>5}% "
          f"events={len(v['events'])}")

print("\n=== conversion by event ===")
for k, v in A["conversion_by_event"].items():
    print(f"  {k:<22} n={v['n']:>5} {v['rate_pct']:>5}%")

print("\n=== conversion by class ===")
for k, v in A["conversion_by_weapon_class"].items():
    print(f"  {k:<10} n={v['n']:>5} {v['rate_pct']:>5}%")

print("\n=== conversion by side ===")
for k, v in A["conversion_by_side"].items():
    print(f"  {k:<10} n={v['n']:>5} {v['rate_pct']:>5}%")

print("\n=== conversion by time ===")
for k, v in A["conversion_by_time_bucket"].items():
    print(f"  {k:<10} n={v['n']:>5} {v['rate_pct']:>5}%")

print("\n=== top 8 agents ===")
for a in A["agents"][:8]:
    print(f"  {a['agent']:<12} {a['first_bloods']:>5}  {a['share_pct']}%")

print("\n=== top 8 weapons ===")
for w in A["weapons"][:8]:
    print(f"  {w['weapon']:<12} {w['class']:<8} {w['first_bloods']:>5}  {w['share_pct']}%")
