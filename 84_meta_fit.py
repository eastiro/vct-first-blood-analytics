"""Recompute meta fit / comp consistency with a correct team tag mapping."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\valorant-analytics")
TAGMAP = json.loads((BASE / "_cache" / "tag_map.json").read_text(encoding="utf-8"))

rows = []
with (BASE / "data" / "rounds.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            rows.append(json.loads(line))


def mean(xs):
    return sum(xs)/len(xs) if xs else 0.0


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = mean(xs), mean(ys)
    num = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x-mx)**2 for x in xs))
    dy = math.sqrt(sum((y-my)**2 for y in ys))
    return num/(dx*dy) if dx and dy else 0.0


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0]*len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    return pearson(rank(xs), rank(ys))


geo = [r for r in rows if r.get("loadouts")]
print(f"rounds with full comps: {len(geo)}")

# top-7 agents per map (computed over ALL rounds of that map)
per_map_agent = defaultdict(Counter)
for r in geo:
    for ld in r["loadouts"]:
        if ld.get("agent"):
            per_map_agent[r["map"]][ld["agent"].lower()] += 1

meta = {mp: {a for a, _ in c.most_common(7)} for mp, c in per_map_agent.items()}

tm = defaultdict(lambda: {"rounds": 0, "wins": 0, "fit": [], "comps": []})
unmapped = Counter()

for r in geo:
    win = r.get("winner_team") or ""
    by_tag = defaultdict(list)
    for ld in r["loadouts"]:
        if ld.get("agent"):
            by_tag[ld["team"]].append(ld["agent"].lower())
    m = meta[r["map"]]
    for tag, agents in by_tag.items():
        name = TAGMAP.get(tag)
        if not name:
            unmapped[tag] += 1
            continue
        if len(agents) != 5:
            continue
        d = tm[name]
        d["rounds"] += 1
        d["wins"] += int(name == win)
        d["fit"].append(sum(1 for a in agents if a in m) / 5)
        d["comps"].append(tuple(sorted(agents)))

if unmapped:
    print(f"unmapped tags: {dict(unmapped)}")

teams = [(t, d) for t, d in tm.items() if d["rounds"] >= 100]
print(f"teams with >=100 rounds: {len(teams)}")

ws = [100*d["wins"]/d["rounds"] for _, d in teams]
print(f"  win% range: {min(ws):.1f} .. {max(ws):.1f}")

xs = [mean(d["fit"]) for _, d in teams]
print(f"\n  meta fit vs round win%:      r = {pearson(xs, ws):+.3f}  "
      f"rho = {spearman(xs, ws):+.3f}")

cc = []
for t, d in teams:
    top = Counter(d["comps"]).most_common(1)[0][1]
    d["consistency"] = top / len(d["comps"])
    cc.append(d["consistency"])
print(f"  comp consistency vs win%:    r = {pearson(cc, ws):+.3f}  "
      f"rho = {spearman(cc, ws):+.3f}")

print(f"\n  {'team':<26} {'rounds':>6} {'metafit':>8} {'consist':>8} {'win%':>6}")
print("  --- most on-meta ---")
for t, d in sorted(teams, key=lambda kv: -mean(kv[1]["fit"]))[:10]:
    print(f"  {t[:26]:<26} {d['rounds']:>6} {mean(d['fit']):>8.2f} "
          f"{d['consistency']:>8.2f} {100*d['wins']/d['rounds']:>6.1f}")
print("  --- least on-meta ---")
for t, d in sorted(teams, key=lambda kv: mean(kv[1]["fit"]))[:10]:
    print(f"  {t[:26]:<26} {d['rounds']:>6} {mean(d['fit']):>8.2f} "
          f"{d['consistency']:>8.2f} {100*d['wins']/d['rounds']:>6.1f}")

print("\n  --- most consistent comps ---")
for t, d in sorted(teams, key=lambda kv: -kv[1]["consistency"])[:8]:
    print(f"  {t[:26]:<26} {d['rounds']:>6} {mean(d['fit']):>8.2f} "
          f"{d['consistency']:>8.2f} {100*d['wins']/d['rounds']:>6.1f}")
