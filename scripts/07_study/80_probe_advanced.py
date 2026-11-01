"""Can we compute TRADED vs UNTRADED first bloods?

Elevated's headline PRX metric is the gap between "untraded first kills" and
"untraded first deaths". A first blood is TRADED when the victim's teammate
kills the first-blood killer shortly after. We have the full kill timeline
with timestamps, so this should be computable.

Also check: do loadouts give us full 5-agent comps per team per round (needed
for Meta Fit / comp consistency)?
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"D:\好玩的项目\vct-first-blood-analytics")

rows = []
with (BASE / "data" / "rounds.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        if line.strip():
            rows.append(json.loads(line))

print(f"rounds: {len(rows)}")

# ---- 1. comps from loadouts -----------------------------------------
geo = [r for r in rows if r.get("loadouts")]
print(f"rounds with loadouts: {len(geo)}")

r0 = geo[0]
by_team = defaultdict(list)
for ld in r0["loadouts"]:
    by_team[ld["team"]].append(ld["agent"])
print(f"\nsample round comps: {r0['event']} / {r0['map']}")
for t, ag in by_team.items():
    print(f"  {t:<28} {sorted(ag)}  (n={len(ag)})")

sizes = Counter(len(v) for r in geo[:500] for v in
                [ [x for x in r["loadouts"] if x["team"]==t]
                  for t in {y["team"] for y in r["loadouts"]} ])
print(f"\ncomp sizes across 500 rounds: {dict(sizes)}")

# ---- 2. traded first blood ------------------------------------------
def first_kill(r):
    ks = [k for k in (r.get("kills") or []) if k.get("killer")]
    if not ks:
        return None
    return min(ks, key=lambda k: (k.get("seconds") if k.get("seconds") is not None else 9999))

TRADE_WINDOW = 5     # seconds

traded = untraded = 0
no_followup = 0
examples = []

for r in rows:
    fk = first_kill(r)
    if not fk:
        continue
    fk_sec = fk.get("seconds")
    killer = fk.get("killer")
    victim = fk.get("victim")
    victim_team = fk.get("victim_team")
    if fk_sec is None or not killer or not victim:
        continue

    is_traded = False
    for k in r["kills"]:
        if k is fk:
            continue
        sec = k.get("seconds")
        if sec is None or sec < fk_sec:
            continue
        if sec - fk_sec > TRADE_WINDOW:
            break
        # victim's teammate avenged it
        if k.get("killer") == victim and False:
            pass
        if (k.get("killer_team") == victim_team
                and k.get("victim") == killer):
            is_traded = True
            break

    if is_traded:
        traded += 1
        if len(examples) < 3:
            examples.append((r, fk))
    else:
        untraded += 1

tot = traded + untraded
print(f"\n=== traded first blood (window {TRADE_WINDOW}s) ===")
print(f"  traded   : {traded:>6}  ({100*traded/tot:.1f}%)")
print(f"  untraded : {untraded:>6}  ({100*untraded/tot:.1f}%)")

print("\nexamples of traced trades:")
for r, fk in examples:
    print(f"  {r['map']:<9} r{r['round']:>2}: {fk['killer']} kills {fk['victim']} "
          f"@ {fk['seconds']}s")
    for k in r["kills"][:4]:
        print(f"      {k['seconds']:>4}s  {k['killer']:<12} -> {k['victim']:<12} "
              f"[{k['killer_team'][:12]} -> {k['victim_team'][:12]}]")
