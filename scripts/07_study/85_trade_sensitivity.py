"""Sensitivity check on the trade window, plus the corrected per-team trade table.

' Traded break-even ' is the key analyst metric: if a first blood is worth X% of
a round, trading it back should roughly cancel it. We test whether the trade
window choice changes the conclusion.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\val-ana\vct-first-blood-analytics")
TAGMAP = json.loads((BASE / "_cache" / "tag_map.json").read_text(encoding="utf-8"))

rows = []
with (BASE / "data" / "rounds.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            rows.append(json.loads(line))


def first_kill(r):
    ks = [k for k in (r.get("kills") or []) if k.get("killer")]
    if not ks:
        return None
    return min(ks, key=lambda k: (k.get("seconds") if k.get("seconds") is not None else 9999))


def is_traded(r, fk, window):
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
        if sec - fk_sec > window:
            break
        if k.get("killer_team") == victim_team and k.get("victim") == killer:
            return True
    return False


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k/n
    d = 1 + z*z/n
    c = p + z*z/(2*n)
    m = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return (100*(c-m)/d, 100*(c+m)/d)


print("=== trade-window sensitivity ===")
print(f"  {'window':<8} {'traded%':>9} {'conv(traded)':>14} {'conv(untraded)':>16} {'gap':>8}")
for w in (2, 3, 5, 8, 10, 15):
    agg = {"t": [0, 0], "u": [0, 0]}
    for r in rows:
        fk = first_kill(r)
        if not fk:
            continue
        tr = is_traded(r, fk, w)
        if tr is None:
            continue
        won = (fk.get("killer_team") or "") == (r.get("winner_team") or "")
        agg["t" if tr else "u"][0] += int(won)
        agg["t" if tr else "u"][1] += 1
    (wt, nt), (wu, nu) = agg["t"], agg["u"]
    share = 100*nt/(nt+nu)
    print(f"  {w:<8} {share:>8.1f}% {100*wt/nt:>13.1f}% {100*wu/nu:>15.1f}% "
          f"{100*wu/nu - 100*wt/nt:>+7.1f}")

# ---- per-team, window 5, corrected mapping -------------------------
W = 5
print(f"\n=== per-team trade profile (window {W}s) ===")
tp = defaultdict(lambda: {"fb":0, "fbU":0, "fd":0, "fdU":0, "rounds":0, "wins":0})
unmapped = set()

for r in rows:
    win = r.get("winner_team") or ""
    fk = first_kill(r)
    if not fk:
        continue
    tr = is_traded(r, fk, W)
    if tr is None:
        continue
    kt, vt = fk.get("killer_team") or "", fk.get("victim_team") or ""
    for who in (kt, vt):
        if who and who not in TAGMAP.values():
            unmapped.add(who)
    if kt:
        tp[kt]["fb"] += 1
        if not tr: tp[kt]["fbU"] += 1
    if vt:
        tp[vt]["fd"] += 1
        if not tr: tp[vt]["fdU"] += 1
    tp[kt]["rounds"] += 1
    tp[kt]["wins"] += int(kt == win)
    tp[vt]["rounds"] += 1
    tp[vt]["wins"] += int(vt == win)

if unmapped:
    print(f"  full names not in tag map: {sorted(unmapped)[:8]}")

out = []
for t, d in tp.items():
    if d["fb"] < 100 or d["fd"] < 50:
        continue
    uk = 100*d["fbU"]/d["fb"]
    ud = 100*d["fdU"]/d["fd"]
    wr = 100*d["wins"]/d["rounds"] if d["rounds"] else 0
    out.append((t, d["fb"], uk, ud, uk-ud, wr))

out.sort(key=lambda x: -x[4])
print(f"  {'team':<26} {'FB':>5} {'untradedFB%':>12} {'untradedFD%':>12} {'gap':>7} {'win%':>6}")
print("  --- best at denying trades on their FB ---")
for t, n, uk, ud, gap, wr in out[:12]:
    print(f"  {t[:26]:<26} {n:>5} {uk:>12.1f} {ud:>12.1f} {gap:>+7.1f} {wr:>6.1f}")
print("  --- worst ---")
for t, n, uk, ud, gap, wr in out[-8:]:
    print(f"  {t[:26]:<26} {n:>5} {uk:>12.1f} {ud:>12.1f} {gap:>+7.1f} {wr:>6.1f}")

# does the gap predict win%?
xs = [o[4] for o in out]
ys = [o[5] for o in out]
mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
num = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
dx = math.sqrt(sum((x-mx)**2 for x in xs))
dy = math.sqrt(sum((y-my)**2 for y in ys))
print(f"\n  trade gap vs win%: r = {num/(dx*dy):+.3f}  (n={len(out)} teams)")
