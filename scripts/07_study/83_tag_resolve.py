"""Derive the team tag -> full name mapping from full 5-agent comps.

In one round, the loadout block gives one 5-agent comp per TEAM TAG, and the
round already tells us both full team names. To pair them, we exploit the
winner: the tag whose players match the winning team is the winner. We get
that from the kill feed (killer_team is a full name, and the killer's agent
is in the tag's comp).

Simpler and exact: build the mapping by frequency across the whole dataset.
Each tag appears alongside exactly one full name in practice (a tag is one
org), so for every round we score tag->name possibilities by co-occurrence,
then resolve greedily.
"""
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

# co-occurrence: a tag and a full name appear in the same round only if they
# are the same team OR an opponent. Both are weak. Use the KILL FEED instead:
# every kill names killer_team (full) and killer_agent; and the loadout block
# tells us which tag owns that agent. Agents can repeat across teams though,
# so instead use uniqueness of (team, agent) pairs.

# Better: the winner_team is a full name. The winning team's players appear as
# killers. Take the round's killer list with full team names and agents, and
# the loadout comps by tag; match a tag to a name when that name's killers'
# agents are all inside the tag's comp.

tag_agents = {}     # per round: tag -> set(agents)
name_agents = {}    # per round: full name -> set(agents seen killing)

score = defaultdict(Counter)

for r in rows:
    lds = r.get("loadouts") or []
    if len(lds) != 10:
        continue
    tags = defaultdict(set)
    for ld in lds:
        if ld.get("agent"):
            tags[ld["team"]].add(ld["agent"].lower())
    if len(tags) != 2:
        continue

    names = defaultdict(set)
    for k in r.get("kills") or []:
        a = (k.get("killer_agent") or "").lower()
        t = k.get("killer_team") or ""
        if a and t:
            names[t].add(a)
    if len(names) != 2:
        continue

    tag_list = list(tags)
    name_list = list(names)
    # try both pairings; pick the one with better containment
    def fit(tg, nm):
        if not names[nm]:
            return 0
        return len(names[nm] & tags[tg]) / len(names[nm])

    direct = sum(fit(tags_k, names_k) for tags_k, names_k in zip(tag_list, name_list))
    cross = sum(fit(tags_k, names_k) for tags_k, names_k in zip(tag_list, reversed(name_list)))
    if direct >= cross:
        pairs = zip(tag_list, name_list)
    else:
        pairs = zip(tag_list, reversed(name_list))
    for tg, nm in pairs:
        score[tg][nm] += 1

# resolve: best full name per tag
mapping = {}
for tg, c in score.items():
    nm, n = c.most_common(1)[0]
    total = sum(c.values())
    mapping[tg] = (nm, n, total)

print(f"resolved tags: {len(mapping)}")
ambig = [(t, nm, n, tot) for t, (nm, n, tot) in mapping.items() if n / tot < 0.9]
print(f"ambiguous (<90% dominant): {len(ambig)}")
for a in ambig[:10]:
    print("   ", a)

print("\n=== mapping ===")
for tg, (nm, n, tot) in sorted(mapping.items()):
    print(f"  {tg:<6} -> {nm:<28} ({n}/{tot})")

out = BASE / "_cache" / "tag_map.json"
out.write_text(json.dumps({t: v[0] for t, v in mapping.items()},
                          ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n-> {out}")
