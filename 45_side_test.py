"""Significance test: attack vs defense first-blood conversion."""
from __future__ import annotations

import json
import math
import sys
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


def two_prop(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se else 0.0
    pval = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, pval


agg = {"attack": [0, 0], "defense": [0, 0]}
for r in rows:
    fk = first_kill(r)
    if not fk:
        continue
    kt = fk.get("killer_team") or ""
    atk = r.get("attacking") or ""
    wt = r.get("winner_team") or ""
    if not kt or not atk or not wt:
        continue
    side = "attack" if kt == atk else "defense"
    agg[side][0] += int(kt == wt)
    agg[side][1] += 1

(wa, na), (wd, nd) = agg["attack"], agg["defense"]
z, p = two_prop(wa, na, wd, nd)
print(f"attack  {wa}/{na} = {100*wa/na:.2f}%")
print(f"defense {wd}/{nd} = {100*wd/nd:.2f}%")
print(f"diff = {100*wa/na - 100*wd/nd:+.2f} pp   z={z:.2f}  p={p:.2e}")

# pistol round only, to separate buy effects
print("\n--- restricted to rounds where the first blood used a pistol ---")
PISTOLS = {"classic", "shorty", "frenzy", "ghost", "sheriff", "bandit"}
ap = {"attack": [0, 0], "defense": [0, 0]}
for r in rows:
    fk = first_kill(r)
    if not fk:
        continue
    cause = (fk.get("cause") or "").strip().lower()
    if cause not in PISTOLS:
        continue
    kt = fk.get("killer_team") or ""
    atk = r.get("attacking") or ""
    wt = r.get("winner_team") or ""
    if not kt or not atk or not wt:
        continue
    side = "attack" if kt == atk else "defense"
    ap[side][0] += int(kt == wt)
    ap[side][1] += 1
(wa2, na2), (wd2, nd2) = ap["attack"], ap["defense"]
z2, p2 = two_prop(wa2, na2, wd2, nd2)
print(f"attack  {wa2}/{na2} = {100*wa2/na2:.2f}%")
print(f"defense {wd2}/{nd2} = {100*wd2/nd2:.2f}%")
print(f"diff = {100*wa2/na2 - 100*wd2/nd2:+.2f} pp   z={z2:.2f}  p={p2:.2e}")
