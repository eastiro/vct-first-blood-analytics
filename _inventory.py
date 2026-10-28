"""Inventory the fields available from HenrikDev /v3/matches.

Answers the only question that matters right now: is this data rich enough to
support round-level tactical analysis, and what are its gaps?
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

KEY = os.environ.get("HDEV", "")
URL = "https://api.henrikdev.xyz/valorant/v3/matches/eu/Henrik3/VALO?size=1"
CACHE = Path(r"D:\好玩的项目\valorant-analytics\_sample_match.json")


def fetch() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    req = urllib.request.Request(
        URL,
        headers={
            "Authorization": KEY,
            # Cloudflare rejects the default urllib agent with 403.
            "User-Agent": "valorant-analytics-research/0.1 (student project)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read().decode("utf-8"))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def keys_of(obj, depth=0, maxdepth=2):
    if not isinstance(obj, dict) or depth > maxdepth:
        return []
    out = []
    for k, v in obj.items():
        if isinstance(v, dict):
            out.append((depth, k, "dict"))
        elif isinstance(v, list):
            out.append((depth, k, f"list[{len(v)}]"))
        else:
            out.append((depth, k, type(v).__name__))
    return out


def main() -> None:
    data = fetch()
    m = data["data"][0]

    print("=" * 70)
    print("MATCH-LEVEL FIELDS")
    print("=" * 70)
    for d, k, t in keys_of(m):
        print(f"  {k:<28} {t}")

    meta = m["metadata"]
    print("\nmetadata:")
    for k, v in meta.items():
        if not isinstance(v, (dict, list)):
            print(f"    {k:<24} {v}")

    print("\n" + "=" * 70)
    print("ROUND STRUCTURE")
    print("=" * 70)
    rounds = m.get("rounds", [])
    print(f"  rounds: {len(rounds)}")
    r0 = rounds[0]
    for d, k, t in keys_of(r0, maxdepth=1):
        print(f"  {k:<28} {t}")

    print("\n  round[0] scalars:")
    for k, v in r0.items():
        if not isinstance(v, (dict, list)):
            print(f"    {k:<24} {v}")

    print("\n  round[0]['plant'] / ['defuse']:")
    for sec in ("plant", "defuse"):
        if sec in r0:
            print(f"    {sec}: {json.dumps(r0[sec], ensure_ascii=False)[:300]}")

    print("\n  round[0]['stats'] (per-player round stats):")
    if "stats" in r0 and r0["stats"]:
        s = r0["stats"][0]
        for d, k, t in keys_of(s, maxdepth=1):
            print(f"    {k:<26} {t}")
        print("\n    player[0] economy:")
        print(json.dumps(s.get("economy", {}), ensure_ascii=False)[:400])

    print("\n" + "=" * 70)
    print("KILLS")
    print("=" * 70)
    kills = m.get("kills", [])
    print(f"  total kills: {len(kills)}")
    k0 = kills[0]
    for d, k, t in keys_of(k0, maxdepth=1):
        print(f"  {k:<28} {t}")

    print("\n" + "=" * 70)
    print("PLAYERS (aggregate)")
    print("=" * 70)
    p0 = m["players"]["all_players"][0]
    for d, k, t in keys_of(p0, maxdepth=1):
        print(f"  {k:<28} {t}")


if __name__ == "__main__":
    main()
