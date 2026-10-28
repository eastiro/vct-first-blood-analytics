"""Test the meta-drift claim: London (June) vs the four Stage 2 leagues (Jul-Sep).

Two things to establish:
1. is the agent-mix difference bigger than sampling noise?
2. does first-blood conversion differ by event beyond noise?
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
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


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (100 * (c - m) / d, 100 * (c + m) / d)


def conv(ev_filter) -> tuple[int, int]:
    n = won = 0
    for r in rows:
        if not ev_filter(r):
            continue
        fk = first_kill(r)
        if not fk:
            continue
        kt = fk.get("killer_team") or ""
        w = r.get("winner_team") or ""
        if not kt or not w:
            continue
        n += 1
        won += int(kt == w)
    return won, n


def two_prop(k1, n1, k2, n2):
    """Two-proportion z-test (pooled)."""
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (p1 - p2) / se
    # normal survival
    pval = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return z, pval


print("=== first-blood -> round win, by event (95% Wilson CI) ===")
per_ev = {}
for ev in ["Masters London 2026", "VCT Americas Stage 2", "VCT EMEA Stage 2",
           "VCT China Stage 2", "VCT Pacific Stage 2"]:
    w, n = conv(lambda r, e=ev: r["event"] == e)
    lo, hi = wilson(w, n)
    per_ev[ev] = (w, n)
    print(f"  {ev:<22} {w:>5}/{n:<5} = {100*w/n:>5.1f}%   CI [{lo:.1f}, {hi:.1f}]")

w1, n1 = per_ev["Masters London 2026"]
w2 = sum(v[0] for k, v in per_ev.items() if k != "Masters London 2026")
n2 = sum(v[1] for k, v in per_ev.items() if k != "Masters London 2026")
z, p = two_prop(w1, n1, w2, n2)
print(f"\n  London vs all Stage 2: {100*w1/n1:.1f}% vs {100*w2/n2:.1f}%  "
      f"z={z:.2f} p={p:.3f}")

print("\n=== agent mix: Jett vs Neon, London vs Stage 2 ===")
for label, flt in [
    ("London", lambda r: r["event"] == "Masters London 2026"),
    ("Stage2", lambda r: r["event"] != "Masters London 2026"),
]:
    c = Counter()
    for r in rows:
        if not flt(r):
            continue
        fk = first_kill(r)
        if fk:
            c[(fk.get("killer_agent") or "?").lower()] += 1
    tot = sum(c.values())
    print(f"  {label:<7} n={tot:<5} jett={c['jett']:>4} ({100*c['jett']/tot:>4.1f}%)  "
          f"neon={c['neon']:>4} ({100*c['neon']/tot:>4.1f}%)  "
          f"raze={c['raze']:>4}  chamber={c['chamber']:>4}  waylay={c['waylay']:>4}")

    if label == "London":
        lc, lt = c, tot
    else:
        sc, st = c, tot

for agent in ("jett", "neon", "chamber", "waylay", "raze"):
    z, p = two_prop(lc[agent], lt, sc[agent], st)
    print(f"    {agent:<8} {100*lc[agent]/lt:>5.1f}% vs {100*sc[agent]/st:>5.1f}%  "
          f"z={z:>6.2f}  p={p:.4f}")

print("\n=== weapon class conversion (95% CI) ===")
WEAPONS = {
    "classic": "pistol", "shorty": "pistol", "frenzy": "pistol", "ghost": "pistol",
    "sheriff": "pistol", "bandit": "pistol",
    "stinger": "smg", "spectre": "smg",
    "bucky": "shotgun", "judge": "shotgun",
    "bulldog": "rifle", "guardian": "rifle", "phantom": "rifle", "vandal": "rifle",
    "marshal": "sniper", "outlaw": "sniper", "operator": "sniper",
    "ares": "lmg", "odin": "lmg", "melee": "melee",
}
agg = {}
for r in rows:
    fk = first_kill(r)
    if not fk:
        continue
    kt = fk.get("killer_team") or ""
    w = r.get("winner_team") or ""
    if not kt or not w:
        continue
    cause = (fk.get("cause") or "").strip().lower()
    cls = WEAPONS.get(cause, "ability")
    d = agg.setdefault(cls, [0, 0])
    d[0] += int(kt == w)
    d[1] += 1

for cls, (w, n) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
    lo, hi = wilson(w, n)
    print(f"  {cls:<9} {w:>5}/{n:<5} = {100*w/n:>5.1f}%  CI [{lo:.1f}, {hi:.1f}]")

print("\n=== attack vs defense first blood (95% CI) ===")
for side in ("attack", "defense"):
    w = n = 0
    for r in rows:
        fk = first_kill(r)
        if not fk:
            continue
        kt = fk.get("killer_team") or ""
        atk = r.get("attacking") or ""
        wt = r.get("winner_team") or ""
        if not kt or not atk or not wt:
            continue
        if (kt == atk) != (side == "attack"):
            continue
        n += 1
        w += int(kt == wt)
    lo, hi = wilson(w, n)
    print(f"  {side:<8} {w:>5}/{n:<5} = {100*w/n:>5.1f}%  CI [{lo:.1f}, {hi:.1f}]")
