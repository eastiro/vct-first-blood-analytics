"""Print the official zh-CN names from the cache (avoids shell quoting)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"D:\好玩的项目\vct-first-blood-analytics\_cache\zh_names.json")
d = json.loads(p.read_text(encoding="utf-8"))
ab, w, ag = d["abilities"], d["weapons"], d["agents"]

print("=== abilities ===")
for k in ("headhunter", "tour de force", "blade storm", "hunter's fury",
          "overdrive", "showstopper", "paint shells", "blast pack",
          "snake bite", "recon bolt", "shock bolt", "incendiary",
          "nanoswarm", "butterfly knives", "hunters fury", "knife"):
    print(f"  {k:<20} -> {ab.get(k, '<<MISSING>>')}")

print("\n=== weapons ===")
for k in ("phantom", "vandal", "operator", "ghost", "outlaw", "sheriff",
          "classic", "spectre", "bandit", "marshal", "guardian", "bulldog",
          "stinger", "frenzy", "judge", "odin", "ares", "shorty", "bucky"):
    print(f"  {k:<12} -> {w.get(k, '<<MISSING>>')}")

print("\n=== agents ===")
for k in ("chamber", "neon", "jett", "sova", "omen", "sage", "cypher",
          "phoenix", "yoru", "vyse", "waylay", "raze", "killjoy", "fade", "tejo"):
    print(f"  {k:<12} -> {ag.get(k, '<<MISSING>>')}")
