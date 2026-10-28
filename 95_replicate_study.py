"""Replicate the Roux Institute / Omnic study's published numbers on our VCT sample.

Their paper (145,456,352 rounds / 7,000,653 matches) reports:
  - first blood -> round win 68.58% (68.28-68.86 across 9 maps)
  - full buy vs eco -> 85.0% ; eco vs full -> 15.9%
  - pistol winner takes round 2 ~8/10 ; pistol loser wins round 3 ~6/10
  - only 16.67% buy a shield in the pistol round ; 41.8% buy a Ghost
"""
import json, collections
from collections import defaultdict

d = json.load(open("data/site_v5.json", encoding="utf-8"))
R, D = d["rounds"], d["dict"]
raw = [json.loads(l) for l in open("data/rounds_all.jsonl", encoding="utf-8")]

print("=== 1. first blood -> round win ===")
fb = [r for r in R if r[5] >= 0]
g = 100 * sum(1 for r in fb if r[4] == r[5]) / len(fb)
print(f"  ours {g:.2f}%  (n={len(fb)})   Roux 68.58%   delta {g-68.58:+.2f}pp")
per_map = {}
for i, m in enumerate(D["maps"]):
    s = [r for r in fb if r[1] == i]
    if len(s) >= 200:
        per_map[m] = 100 * sum(1 for r in s if r[4] == r[5]) / len(s)
lo, hi = min(per_map.values()), max(per_map.values())
print(f"  per-map spread {lo:.2f}% .. {hi:.2f}%  (spread {hi-lo:.2f}pp)"
      f"   Roux 68.28..68.86 (spread 0.58pp)")

print("\n=== 2. full buy vs eco (buy class from long guns held) ===")
full_vs_eco = [0, 0]
for r in R:
    if r[16] < 0 or r[17] < 0:
        continue
    for mine_t, mine_e, theirs_e in ((r[2], r[16], r[17]), (r[3], r[17], r[16])):
        if mine_e == 2 and theirs_e == 0:
            full_vs_eco[0] += 1
            if r[4] == mine_t:
                full_vs_eco[1] += 1
n, w = full_vs_eco
print(f"  full vs eco -> {100*w/n:.1f}%  (n={n})   Roux 85.0%   delta {100*w/n-85.0:+.1f}pp")
print(f"  eco vs full -> {100-100*w/n:.1f}%  (mirror)   Roux 15.9%")

print("\n=== 3. pistol round chain ===")
games = collections.defaultdict(list)
for r in R:
    games[r[20]].append(r)
w2 = [0, 0]
r3_loser = [0, 0]
r3_winner = [0, 0]
for rs in games.values():
    pm = {r[18]: r for r in rs if r[18] in (1, 13)}
    for pno, r2no, r3no in ((1, 2, 3), (13, 14, 15)):
        p = pm.get(pno)
        if not p:
            continue
        rip = p[4]
        lose = p[2] if p[4] == p[3] else p[3]
        r2 = next((r for r in rs if r[18] == r2no), None)
        r3 = next((r for r in rs if r[18] == r3no), None)
        if r2:
            w2[0] += 1
            if r2[4] == rip:
                w2[1] += 1
        if r3:
            r3_loser[0] += 1
            if r3[4] == lose:
                r3_loser[1] += 1
            r3_winner[0] += 1
            if r3[4] == rip:
                r3_winner[1] += 1
print(f"  pistol winner also wins round 2: {100*w2[1]/w2[0]:.1f}%  (n={w2[0]})   Roux ~80%")
print(f"  pistol loser  wins round 3     : {100*r3_loser[1]/r3_loser[0]:.1f}%  (n={r3_loser[0]})   Roux ~60%")
print(f"  pistol winner wins round 3     : {100*r3_winner[1]/r3_winner[0]:.1f}%")

print("\n=== 4. pistol round buy (armor / weapon) ===")
armor = collections.Counter()
weap = collections.Counter()
tot = 0
for r in raw:
    if r.get("round") not in (1, 13):
        continue
    for p in r.get("loadouts") or []:
        tot += 1
        a = (p.get("armor") or "").lower()
        armor["none" if ("no" in a or a == "") else a] += 1
        weap[(p.get("weapon") or "").strip()] += 1
print(f"  players in pistol rounds: {tot}")
for k, v in armor.most_common(4):
    print(f"    armor {k:12s} {v:6d}  {100*v/tot:5.1f}%")
print(f"  Roux: 16.67% buy a shield")
for k, v in weap.most_common(5):
    print(f"    weapon {k:10s} {v:6d}  {100*v/tot:5.1f}%")
print("  Roux: 41.8% spend on a Ghost")

print("\n=== 5. buy class matrix (mine vs theirs) -> round win ===")
mat = defaultdict(lambda: [0, 0])
nm = {0: "eco", 1: "half", 2: "full"}
for r in R:
    if r[16] < 0:
        continue
    for t, me, th in ((r[2], r[16], r[17]), (r[3], r[17], r[16])):
        mat[(me, th)][0] += 1
        if r[4] == t:
            mat[(me, th)][1] += 1
for k in sorted(mat):
    n, w = mat[k]
    if n < 50:
        continue
    print(f"    mine={nm[k[0]]:<4} vs opp={nm[k[1]]:<4}  n={n:5d}  win {100*w/n:.1f}%")

print("\n=== 6. how often is each buy class seen ===")
seen = defaultdict(int)
for r in R:
    if r[16] < 0:
        continue
    seen[r[16]] += 1
    seen[r[17]] += 1
tot_seen = sum(seen.values())
for k in sorted(seen):
    print(f"    {nm[k]:<4} {seen[k]:6d}  {100*seen[k]/tot_seen:5.1f}% of team-rounds")

print("\n=== 7. absolute spend vs relative spend (the retention confound) ===")
tab = collections.defaultdict(lambda: [0, 0])
for r in R:
    if r[16] < 0:
        continue
    for t, s in ((r[2], r[14]), (r[3], r[15])):
        tab[s // 4000][0] += 1
        if r[4] == t:
            tab[s // 4000][1] += 1
for k in sorted(tab):
    n, w = tab[k]
    if n < 200:
        continue
    print(f"    {k*4:2d}-{k*4+4:2d}k team spend  n={n:5d}  win {100*w/n:.1f}%")

print("\n=== 8. spend vs guns: do they agree? ===")
agree = defaultdict(int)
for r in R:
    if r[16] < 0:
        continue
    for e, g in ((r[16], r[21]), (r[17], r[22])):
        agree[(e, g)] += 1
print("    buy class -> long-gun count distribution")
for e in sorted({k[0] for k in agree}):
    row = {g: c for (ee, g), c in agree.items() if ee == e}
    tot = sum(row.values())
    print(f"    {nm[e]:<4} n={tot:6d}  " +
          "  ".join(f"{g}g:{100*c/tot:.0f}%" for g, c in sorted(row.items())))
