"""Check how team tags map to full names, then recompute meta fit correctly."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")

rows = []
with (BASE / "data" / "rounds.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            rows.append(json.loads(line))

# For a few rounds, show tag(from loadout) vs full name(from teams/winner)
print("=== tag vs full name mapping ===")
seen = set()
for r in rows:
    if not r.get("loadouts"):
        continue
    tags = sorted({ld["team"] for ld in r["loadouts"]})
    key = tuple(tags)
    if key in seen or len(seen) > 5:
        continue
    seen.add(key)
    t1, t2 = (r["teams"].split(" vs ") + ["", ""])[:2]
    print(f"  {r['map']:<9} tags={tags}")
    print(f"             teams={t1!r} / {t2!r}   winner={r['winner_team']!r}")

# Build tag -> full name by pairing: in each round, tags and team names should
# be the two teams. But we can't tell which tag is which... except the winner
# appears as winner_team. Let's check if tags ever equal full names.
all_tags = Counter()
all_names = Counter()
for r in rows:
    t1, t2 = (r["teams"].split(" vs ") + ["", ""])[:2]
    all_names[t1] += 1
    all_names[t2] += 1
    for ld in r.get("loadouts", []):
        all_tags[ld["team"]] += 1

print(f"\ndistinct tags: {len(all_tags)}  distinct full names: {len(all_names)}")
overlap = set(all_tags) & set(all_names)
print(f"tags that are also full names: {len(overlap)} -> {sorted(overlap)[:10]}")
print(f"\nfirst 12 tags: {[t for t,_ in all_tags.most_common(12)]}")
print(f"first 12 names: {[t for t,_ in all_names.most_common(12)]}")
