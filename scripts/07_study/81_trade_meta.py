"""Validate the two analyst metrics before building them into the site.

1. TRADE: does an untraded first blood convert better than a traded one?
   Intuition: traded FB means you went 1-for-1, so the man advantage is gone.
2. META FIT: fraction of a team's comp that matches the map's global top-7
   agents. Elevated found ~no correlation with winning (r=+0.046 over 425
   team-events) - check whether that reproduces here.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\valorant-analytics")

rows = []
with (BASE / "data" / "rounds.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            rows.append(json.loads(line))

TRADE_WINDOW = 5


def first_kill(r):
    ks = [k for k in (r.get("kills") or []) if k.get("killer")]
    if not ks:
        return None
    return min(ks, key=lambda k: (k.get("seconds") if k.get("seconds") is not None else 9999))


def was_traded(r, fk):
    fk_sec = fk.get("seconds")
    killer = fk.get("killer")
    victim_team = fk.get("victim_team")
    if fk_sec is None or not killer or not victim_team:
        return None
    for k in r["kills"]:
        if k is fk:
            continue
        sec = k.get("seconds")
        if sec is None or sec < fk_sec:
            continue
        if sec - fk_sec > TRADE_WINDOW:
            break
        if k.get("killer_team") == victim_team and k.get("victim") == killer:
            return True
    return False


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z*z/n
    c = p + z*z/(2*n)
    m = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return (100*(c-m)/d, 100*(c+m)/d)


# ======================================================================
# 1. traded vs untraded first blood -> round win
# ======================================================================
print("=== does trading the first blood change the round? ===")
agg = {"traded": [0, 0], "untraded": [0, 0]}
for r in rows:
    fk = first_kill(r)
    if not fk:
        continue
    tr = was_traded(r, fk)
    if tr is None:
        continue
    won = (fk.get("killer_team") or "") == (r.get("winner_team") or "")
    key = "traded" if tr else "untraded"
    agg[key][0] += int(won)
    agg[key][1] += 1

for key, (w, n) in agg.items():
    lo, hi = wilson(w, n)
    print(f"  {key:<9} {w:>5}/{n:<6} = {100*w/n:>5.1f}%  CI [{lo:.1f}, {hi:.1f}]")

(w1, n1), (w2, n2) = agg["traded"], agg["untraded"]
p = (w1+w2)/(n1+n2)
se = math.sqrt(p*(1-p)*(1/n1+1/n2))
z = ((w1/n1)-(w2/n2))/se
pval = 2*(1-0.5*(1+math.erf(abs(z)/math.sqrt(2))))
print(f"  diff = {100*w1/n1 - 100*w2/n2:+.1f} pp   z={z:.2f}  p={pval:.2e}")

# ======================================================================
# 2. meta fit
# ======================================================================
print("\n=== meta fit ===")
geo = [r for r in rows if r.get("loadouts")]
print(f"rounds with full comps: {len(geo)}")

# global top-7 agents per map
per_map_agent = defaultdict(Counter)
for r in geo:
    teams = {ld["team"] for ld in r["loadouts"]}
    for t in teams:
        for ld in r["loadouts"]:
            if ld["team"] == t and ld["agent"]:
                per_map_agent[r["map"]][ld["agent"].lower()] += 1

meta_agents = {}
for mp, c in per_map_agent.items():
    meta_agents[mp] = {a for a, _ in c.most_common(7)}
    print(f"  {mp:<9} top7: {sorted(meta_agents[mp])}")

# per team: meta fit and round win rate
tm = defaultdict(lambda: {"rounds": 0, "wins": 0, "fit": [], "comps": []})
for r in geo:
    teams = {ld["team"] for ld in r["loadouts"]}
    win = r.get("winner_team") or ""
    meta = meta_agents[r["map"]]
    for t in teams:
        agents = [ld["agent"].lower() for ld in r["loadouts"]
                  if ld["team"] == t and ld["agent"]]
        if len(agents) != 5:
            continue
        fit = sum(1 for a in agents if a in meta) / 5
        d = tm[t]
        d["rounds"] += 1
        d["wins"] += int(t == win)
        d["fit"].append(fit)
        d["comps"].append(tuple(sorted(agents)))

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

teams = [(t, d) for t, d in tm.items() if d["rounds"] >= 100]
print(f"\nteams with >=100 rounds: {len(teams)}")

xs = [mean(d["fit"]) for _, d in teams]
ys = [100*d["wins"]/d["rounds"] for _, d in teams]
r_val = pearson(xs, ys)
print(f"  meta fit vs round win%:  r = {r_val:+.3f}")

# comp consistency = share of rounds spent on the team's single most-used comp
for t, d in teams:
    cc = Counter(d["comps"]).most_common(1)[0][1] / len(d["comps"])
    d["consistency"] = cc
xs2 = [d["consistency"] for _, d in teams]
r2 = pearson(xs2, ys)
print(f"  comp consistency vs win%: r = {r2:+.3f}")

print(f"\n  {'team':<26} {'rounds':>6} {'metafit':>8} {'consist':>8} {'win%':>6}")
for t, d in sorted(teams, key=lambda kv: -mean(kv[1]["fit"]))[:12]:
    print(f"  {t[:26]:<26} {d['rounds']:>6} {mean(d['fit']):>8.2f} "
          f"{d['consistency']:>8.2f} {100*d['wins']/d['rounds']:>6.1f}")
print("  ...")
for t, d in sorted(teams, key=lambda kv: mean(kv[1]["fit"]))[:6]:
    print(f"  {t[:26]:<26} {d['rounds']:>6} {mean(d['fit']):>8.2f} "
          f"{d['consistency']:>8.2f} {100*d['wins']/d['rounds']:>6.1f}")

# ======================================================================
# 3. per-team trade profile (Elevated's PRX metric)
# ======================================================================
print("\n=== untraded first kills vs untraded first deaths ===")
tp = defaultdict(lambda: {"fbFor":0,"fbUntradedFor":0,"fdAgainst":0,"fdUntradedAgainst":0})
for r in rows:
    fk = first_kill(r)
    if not fk:
        continue
    tr = was_traded(r, fk)
    if tr is None:
        continue
    kt = fk.get("killer_team") or ""
    vt = fk.get("victim_team") or ""
    if kt:
        tp[kt]["fbFor"] += 1
        if not tr:
            tp[kt]["fbUntradedFor"] += 1
    if vt:
        tp[vt]["fdAgainst"] += 1
        if not tr:
            tp[vt]["fdUntradedAgainst"] += 1

out = []
for t, d in tp.items():
    if d["fbFor"] < 100:
        continue
    uk = 100*d["fbUntradedFor"]/d["fbFor"]
    ud = 100*d["fdUntradedAgainst"]/d["fdAgainst"] if d["fdAgainst"] else 0
    out.append((t, d["fbFor"], uk, ud, uk-ud))

out.sort(key=lambda x: -x[4])
print(f"  {'team':<26} {'FB':>5} {'untraded FB%':>13} {'untraded FD%':>13} {'gap':>7}")
for t, n, uk, ud, gap in out[:10]:
    print(f"  {t[:26]:<26} {n:>5} {uk:>13.1f} {ud:>13.1f} {gap:>+7.1f}")
print("  ...")
for t, n, uk, ud, gap in out[-5:]:
    print(f"  {t[:26]:<26} {n:>5} {uk:>13.1f} {ud:>13.1f} {gap:>+7.1f}")
